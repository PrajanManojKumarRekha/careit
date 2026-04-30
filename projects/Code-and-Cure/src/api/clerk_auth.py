import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from src.api.config import (
    CLERK_API_URL,
    CLERK_JWKS_URL,
    CLERK_JWT_AUDIENCE,
    CLERK_JWT_ISSUER,
    CLERK_SECRET_KEY,
)
from src.database.db_client import (
    get_or_create_doctor_profile,
    get_user_by_clerk_user_id,
    upsert_clerk_user,
)

_JWKS_CACHE_SECONDS = 300
_jwks_cache: dict[str, Any] = {"value": None, "expires_at": 0.0}


def _require_clerk_auth_config() -> None:
    if not CLERK_JWKS_URL or not CLERK_JWT_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk authentication is not configured on the API.",
        )


def _get_jwks() -> dict[str, Any]:
    _require_clerk_auth_config()
    now = time.time()
    cached = _jwks_cache.get("value")
    if cached and now < float(_jwks_cache.get("expires_at") or 0):
        return cached

    try:
        response = httpx.get(CLERK_JWKS_URL, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve Clerk signing keys.",
        ) from exc

    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise HTTPException(status_code=503, detail="Invalid Clerk JWKS response.")

    _jwks_cache["value"] = payload
    _jwks_cache["expires_at"] = now + _JWKS_CACHE_SECONDS
    return payload


def verify_clerk_session_token(token: str) -> dict[str, Any]:
    jwks = _get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token.") from exc

    kid = header.get("kid")
    matching_key = next((key for key in jwks["keys"] if key.get("kid") == kid), None)
    if not matching_key:
        raise HTTPException(status_code=401, detail="Authentication token signing key not recognized.")

    options = {
        "verify_aud": bool(CLERK_JWT_AUDIENCE),
        "verify_iss": True,
    }
    try:
        claims = jwt.decode(
            token,
            matching_key,
            algorithms=[header.get("alg", "RS256")],
            audience=CLERK_JWT_AUDIENCE or None,
            issuer=CLERK_JWT_ISSUER,
            options=options,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.") from exc

    if claims.get("azp") in {"", None}:
        raise HTTPException(status_code=401, detail="Authentication token is missing the authorized party.")
    return claims


def _pick_primary_email(user_payload: dict[str, Any]) -> tuple[str | None, bool]:
    email_addresses = user_payload.get("email_addresses") or []
    primary_email_id = user_payload.get("primary_email_address_id")
    for email_obj in email_addresses:
        if email_obj.get("id") == primary_email_id:
            return email_obj.get("email_address"), bool(email_obj.get("verification", {}).get("status") == "verified")
    if email_addresses:
        email_obj = email_addresses[0]
        return email_obj.get("email_address"), bool(email_obj.get("verification", {}).get("status") == "verified")
    return None, False


def fetch_clerk_user(clerk_user_id: str) -> dict[str, Any]:
    if not CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk secret key is not configured on the API.",
        )

    try:
        response = httpx.get(
            f"{CLERK_API_URL}/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve the authenticated user profile from Clerk.",
        ) from exc
    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail="Invalid Clerk user response.")
    return payload


def _parse_clerk_profile(user_payload: dict[str, Any]) -> dict[str, str | None]:
    email, is_verified = _pick_primary_email(user_payload)
    unsafe_metadata = user_payload.get("unsafe_metadata") or {}
    public_metadata = user_payload.get("public_metadata") or {}
    role = unsafe_metadata.get("role") or public_metadata.get("role")
    first_name = (user_payload.get("first_name") or "").strip()
    last_name = (user_payload.get("last_name") or "").strip()
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()
    full_name = full_name or (user_payload.get("username") or "").strip() or "careIT User"
    verified_at = datetime.now(timezone.utc).isoformat() if is_verified else None
    return {
        "email": email,
        "role": role,
        "full_name": full_name,
        "email_verified_at": verified_at,
    }


def sync_clerk_user(clerk_user_id: str) -> dict[str, Any]:
    user_payload = fetch_clerk_user(clerk_user_id)
    parsed = _parse_clerk_profile(user_payload)
    email = parsed["email"]
    role = parsed["role"]
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated Clerk user is missing a primary email address.")
    if role not in {"patient", "doctor"}:
        raise HTTPException(
            status_code=403,
            detail="Account role is missing. Complete sign-up to continue.",
        )

    local_user = upsert_clerk_user(
        clerk_user_id=clerk_user_id,
        email=email,
        full_name=parsed["full_name"] or "careIT User",
        role=role,
        email_verified_at=parsed["email_verified_at"],
    )
    if not local_user or not local_user.get("id"):
        raise HTTPException(status_code=500, detail="Failed to synchronize the authenticated user.")

    if role == "doctor":
        get_or_create_doctor_profile(local_user["id"])
    return local_user


def resolve_authenticated_user(token: str) -> dict[str, Any]:
    claims = verify_clerk_session_token(token)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Authentication token is missing the subject.")

    local_user = get_user_by_clerk_user_id(clerk_user_id)
    if not local_user or local_user.get("role") not in {"patient", "doctor"}:
        local_user = sync_clerk_user(clerk_user_id)

    return {
        "user_id": local_user["id"],
        "role": local_user["role"],
        "email": local_user["email"],
        "full_name": local_user["full_name"],
        "clerk_user_id": clerk_user_id,
    }
