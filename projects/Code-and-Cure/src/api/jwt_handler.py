import os
from datetime import datetime, timedelta

from fastapi import HTTPException
from jose import JWTError, jwt

from src.api.config import JWT_SECRET_KEY
from src.api.clerk_auth import resolve_authenticated_user

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24
ISSUER = os.getenv("JWT_ISSUER", "careit-api")


def create_token(payload: dict) -> str:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be set to mint legacy application tokens.")
    data = payload.copy()
    now = datetime.utcnow()
    data["exp"] = now + timedelta(hours=TOKEN_EXPIRY_HOURS)
    data["iat"] = now
    data["iss"] = ISSUER
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def decode_legacy_token(token: str) -> dict:
    if not SECRET_KEY:
        raise HTTPException(status_code=401, detail="Legacy authentication is not configured.")
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer=ISSUER)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def decode_token(token: str) -> dict:
    if token.count(".") != 2:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    if SECRET_KEY:
        try:
            return decode_legacy_token(token)
        except HTTPException:
            pass
    return resolve_authenticated_user(token)
