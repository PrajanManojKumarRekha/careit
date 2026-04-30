from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.config import ALLOW_DEMO_MODE
from src.api.dependencies import get_current_user
from src.api.jwt_handler import create_token
from src.api.models import DemoLoginRequest
from src.database.db_client import (
    get_or_create_doctor_profile,
    get_user_by_email,
    insert_user,
    update_user_auth_state,
)

router = APIRouter()


_CLERK_ONLY_MESSAGE = (
    "This API now uses Clerk-managed authentication. Complete sign-in and sign-up from the Next.js frontend."
)

_DEMO_ACCOUNTS = {
    "patient": {
        "email": "demo.patient@careit.local",
        "full_name": "Demo Patient",
        "role": "patient",
    },
    "doctor": {
        "email": "demo.doctor@careit.local",
        "full_name": "Demo Doctor",
        "role": "doctor",
    },
}


def _ensure_demo_user(role: str) -> dict:
    account = _DEMO_ACCOUNTS[role]
    existing = get_user_by_email(account["email"])
    if existing:
        if existing.get("role") != role or existing.get("full_name") != account["full_name"]:
            existing = update_user_auth_state(
                existing["id"],
                role=role,
                full_name=account["full_name"],
                password_hash="DEMO_AUTH_ONLY",
            )
        user = existing
    else:
        user = insert_user(
            email=account["email"],
            password_hash="DEMO_AUTH_ONLY",
            full_name=account["full_name"],
            role=role,
        )

    if role == "doctor":
        get_or_create_doctor_profile(user["id"])
    return user


@router.post("/register", status_code=status.HTTP_410_GONE)
async def register() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/verify-email", status_code=status.HTTP_410_GONE)
async def verify_email() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/resend-verification", status_code=status.HTTP_410_GONE)
async def resend_verification() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/login", status_code=status.HTTP_410_GONE)
async def login() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/login/verify", status_code=status.HTTP_410_GONE)
async def verify_login() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/session")
async def sync_session(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "status": "authenticated",
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    }


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    }


@router.post("/demo-login")
async def demo_login(request: DemoLoginRequest) -> dict:
    if not ALLOW_DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo login is disabled.")

    if request.role == "patient":
        _ensure_demo_user("doctor")

    user = _ensure_demo_user(request.role)
    if not user or not user.get("id"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create demo account.")

    token = create_token(
        {
            "user_id": user["id"],
            "role": user["role"],
            "email": user["email"],
            "full_name": user["full_name"],
        }
    )
    return {
        "status": "authenticated",
        "access_token": token,
        "user_id": user["id"],
        "role": user["role"],
        "email": user["email"],
        "full_name": user["full_name"],
        "message": f"Signed in as demo {user['role']}.",
    }


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="__session", path="/")
    return {"status": "success"}
