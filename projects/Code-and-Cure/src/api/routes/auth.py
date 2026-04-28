import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from passlib.context import CryptContext

from src.api.config import (
    AUTH_CODE_TTL_MINUTES,
    AUTH_LOCKOUT_MINUTES,
    AUTH_LOCKOUT_THRESHOLD,
    AUTH_RETURN_TOKEN_IN_BODY,
    JWT_COOKIE_MAX_AGE_SECONDS,
    JWT_COOKIE_NAME,
    JWT_COOKIE_SAMESITE,
    JWT_COOKIE_SECURE,
)
from src.api.dependencies import get_current_user
from src.api.emailer import EmailDeliveryError, send_auth_code_email
from src.api.jwt_handler import create_token
from src.api.models import (
    AuthChallengeResponse,
    AuthResponse,
    EmailOnlyRequest,
    EmailCodeVerification,
    UserLogin,
    UserRegister,
)
from src.database.db_client import (
    consume_auth_challenge,
    get_active_auth_challenge,
    get_auth_challenge,
    get_user_by_email,
    insert_auth_challenge,
    insert_doctor_profile,
    insert_user,
    invalidate_auth_challenges,
    update_user_auth_state,
)

logger = logging.getLogger(__name__)

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_VERIFICATION_PURPOSE = "email_verification"
LOGIN_MFA_PURPOSE = "login_mfa"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_auth_challenge(user: dict, purpose: str) -> tuple[dict, str]:
    code = _generate_code()
    now = _utcnow()
    invalidate_auth_challenges(user["id"], purpose, now.isoformat())
    challenge = insert_auth_challenge(
        user_id=user["id"],
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=(now + timedelta(minutes=AUTH_CODE_TTL_MINUTES)).isoformat(),
    )
    if not challenge or not challenge.get("id"):
        raise HTTPException(status_code=500, detail="Failed to create authentication challenge.")
    return challenge, code


def _send_email_verification(user: dict, code: str) -> None:
    subject = "Verify your careIT account"
    body = (
        f"Your careIT verification code is {code}.\n\n"
        f"It expires in {AUTH_CODE_TTL_MINUTES} minutes.\n"
        "If you did not create this account, you can ignore this email."
    )
    send_auth_code_email(user["email"], subject, body)


def _send_login_mfa(user: dict, code: str) -> None:
    subject = "Your careIT sign-in code"
    body = (
        f"Your careIT sign-in code is {code}.\n\n"
        f"It expires in {AUTH_CODE_TTL_MINUTES} minutes.\n"
        "If you did not attempt to sign in, reset your password and review recent activity."
    )
    send_auth_code_email(user["email"], subject, body)


def _set_auth_cookie(response: Response, user: dict) -> str:
    token_payload = {
        "user_id": user["id"],
        "role": user["role"],
        "email_verified": bool(user.get("email_verified_at")),
        "amr": ["pwd", "email_otp"],
    }
    token = create_token(token_payload)
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        max_age=JWT_COOKIE_MAX_AGE_SECONDS,
        path="/",
    )
    return token


def _ensure_not_locked(user: dict) -> None:
    locked_until = user.get("locked_until")
    if not locked_until:
        return
    try:
        locked_at = datetime.fromisoformat(str(locked_until).replace("Z", "+00:00"))
    except ValueError:
        return
    if locked_at > _utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to repeated failed login attempts. Please try again later.",
        )


def _register_failed_login(user: dict) -> None:
    attempts = int(user.get("failed_login_attempts") or 0) + 1
    payload: dict[str, object] = {"failed_login_attempts": attempts}
    if attempts >= AUTH_LOCKOUT_THRESHOLD:
        payload["locked_until"] = (_utcnow() + timedelta(minutes=AUTH_LOCKOUT_MINUTES)).isoformat()
        payload["failed_login_attempts"] = 0
    update_user_auth_state(user["id"], **payload)


def _verify_challenge(user: dict, verification: EmailCodeVerification, purpose: str) -> dict:
    if verification.challenge_id:
        challenge = get_auth_challenge(verification.challenge_id)
    else:
        challenge = get_active_auth_challenge(user["id"], purpose)
    if not challenge or challenge.get("user_id") != user["id"] or challenge.get("purpose") != purpose:
        raise HTTPException(status_code=400, detail="Verification challenge not found.")
    if challenge.get("consumed_at"):
        raise HTTPException(status_code=400, detail="Verification code has already been used.")

    expires_at = datetime.fromisoformat(str(challenge["expires_at"]).replace("Z", "+00:00"))
    if expires_at <= _utcnow():
        raise HTTPException(status_code=400, detail="Verification code has expired.")

    if not hmac.compare_digest(challenge["code_hash"], _hash_code(verification.code)):
        raise HTTPException(status_code=401, detail="Invalid verification code.")
    return challenge


@router.post("/register", response_model=AuthChallengeResponse)
async def register(user: UserRegister):
    """
    Registers a new user, stores a bcrypt password hash, and starts email verification.
    """
    if user.role not in ["patient", "doctor"]:
        raise HTTPException(status_code=400, detail="Role must be 'patient' or 'doctor'")

    existing = get_user_by_email(user.email)
    if existing:
        if existing.get("email_verified_at"):
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(
            status_code=409,
            detail="Email already registered but not verified. Use the resend verification flow.",
        )

    hashed_password = pwd_context.hash(user.password)
    row = insert_user(
        email=user.email,
        password_hash=hashed_password,
        full_name=user.full_name,
        role=user.role,
    )

    if not row or not row.get("id"):
        raise HTTPException(status_code=500, detail="Failed to register user.")

    if user.role == "doctor":
        try:
            insert_doctor_profile(
                user_id=row["id"],
                specialty="General Practice",
                license_no="PENDING",
                lat=37.7749,
                lng=-122.4194,
                address="To be updated",
            )
        except Exception as exc:
            logger.warning("Doctor profile creation failed for user %s: %s", row["id"], exc)

    try:
        challenge, code = _issue_auth_challenge({**row, "email": user.email}, EMAIL_VERIFICATION_PURPOSE)
        _send_email_verification({**row, "email": user.email}, code)
    except EmailDeliveryError as exc:
        logger.warning("Registration email delivery failed for %s: %s", user.email, exc)
        raise HTTPException(status_code=503, detail=str(exc))

    return AuthChallengeResponse(
        status="verification_required",
        message=f"Verification code sent to {user.email}.",
        email=user.email,
        challenge_id=challenge["id"],
        role=user.role,
    )


@router.post("/verify-email")
async def verify_email(verification: EmailCodeVerification):
    user = get_user_by_email(verification.email)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    if user.get("email_verified_at"):
        return {"status": "verified", "message": "Email address is already verified."}

    challenge = _verify_challenge(user, verification, EMAIL_VERIFICATION_PURPOSE)
    now = _utcnow().isoformat()
    consume_auth_challenge(challenge["id"], now)
    update_user_auth_state(
        user["id"],
        email_verified_at=now,
        failed_login_attempts=0,
        locked_until=None,
    )
    return {"status": "verified", "message": "Email address verified. You can now sign in."}


@router.post("/resend-verification", response_model=AuthChallengeResponse)
async def resend_verification(request: EmailOnlyRequest):
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    if user.get("email_verified_at"):
        raise HTTPException(status_code=400, detail="Email address is already verified.")

    try:
        challenge, code = _issue_auth_challenge(user, EMAIL_VERIFICATION_PURPOSE)
        _send_email_verification(user, code)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return AuthChallengeResponse(
        status="verification_required",
        message=f"Verification code sent to {request.email}.",
        email=request.email,
        challenge_id=challenge["id"],
        role=user["role"],
    )


@router.post("/login", response_model=AuthChallengeResponse)
async def login(credentials: UserLogin):
    """
    Verifies password, enforces lockout + verified email, then starts email OTP MFA.
    """
    user = get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _ensure_not_locked(user)

    if not pwd_context.verify(credentials.password, user["password_hash"]):
        _register_failed_login(user)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("email_verified_at"):
        raise HTTPException(
            status_code=403,
            detail="Email address is not verified. Complete verification before signing in.",
        )

    try:
        challenge, code = _issue_auth_challenge(user, LOGIN_MFA_PURPOSE)
        _send_login_mfa(user, code)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return AuthChallengeResponse(
        status="mfa_required",
        message=f"Sign-in code sent to {credentials.email}.",
        email=credentials.email,
        challenge_id=challenge["id"],
        role=user["role"],
    )


@router.post("/login/verify", response_model=AuthResponse)
async def verify_login(verification: EmailCodeVerification, response: Response):
    user = get_user_by_email(verification.email)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")

    _ensure_not_locked(user)
    challenge = _verify_challenge(user, verification, LOGIN_MFA_PURPOSE)
    now = _utcnow().isoformat()
    consume_auth_challenge(challenge["id"], now)
    update_user_auth_state(user["id"], failed_login_attempts=0, locked_until=None)
    user = {**user, "email_verified_at": user.get("email_verified_at")}
    token = _set_auth_cookie(response, user)
    return AuthResponse(
        access_token=token if AUTH_RETURN_TOKEN_IN_BODY else None,
        role=user["role"],
        message="Authentication successful.",
    )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        path="/",
    )
    return {"status": "success"}
