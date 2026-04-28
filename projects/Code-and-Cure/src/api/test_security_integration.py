import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import appointments as appointments_routes
from src.api.routes import auth as auth_routes
from src.api.routes import intake as intake_routes
from src.api.security import RateLimitMiddleware
from src.core_logic import transcriber


def test_register_starts_email_verification(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")

    monkeypatch.setattr(auth_routes, "get_user_by_email", lambda email: None)
    monkeypatch.setattr(
        auth_routes,
        "insert_user",
        lambda email, password_hash, full_name, role: {
            "id": "user-123",
            "email": email,
            "full_name": full_name,
            "role": role,
        },
    )
    monkeypatch.setattr(auth_routes, "insert_doctor_profile", lambda *args, **kwargs: {})
    monkeypatch.setattr(auth_routes, "invalidate_auth_challenges", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        auth_routes,
        "insert_auth_challenge",
        lambda user_id, purpose, code_hash, expires_at: {
            "id": "challenge-123",
            "user_id": user_id,
            "purpose": purpose,
            "code_hash": code_hash,
            "expires_at": expires_at,
        },
    )
    monkeypatch.setattr(auth_routes, "send_auth_code_email", lambda *args, **kwargs: None)

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "patient@example.com",
            "password": "ValidPassword123!",
            "full_name": "Patient Example",
            "role": "patient",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "verification_required"
    assert response.json()["challenge_id"] == "challenge-123"


def test_login_verify_sets_http_only_cookie_and_me_accepts_cookie_auth(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")

    password_hash = auth_routes.pwd_context.hash("ValidPassword123!")
    user = {
        "id": "user-123",
        "email": "doctor@example.com",
        "password_hash": password_hash,
        "role": "doctor",
        "email_verified_at": "2026-04-27T12:00:00+00:00",
        "failed_login_attempts": 0,
        "locked_until": None,
    }
    challenge = {
        "id": "challenge-456",
        "user_id": "user-123",
        "purpose": auth_routes.LOGIN_MFA_PURPOSE,
        "code_hash": auth_routes._hash_code("654321"),
        "expires_at": "2099-01-01T00:00:00+00:00",
        "consumed_at": None,
    }

    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda email: user if email == user["email"] else None,
    )
    monkeypatch.setattr(auth_routes, "invalidate_auth_challenges", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        auth_routes,
        "insert_auth_challenge",
        lambda user_id, purpose, code_hash, expires_at: {
            "id": "challenge-456",
            "user_id": user_id,
            "purpose": purpose,
            "code_hash": code_hash,
            "expires_at": expires_at,
        },
    )
    monkeypatch.setattr(auth_routes, "send_auth_code_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth_routes, "get_auth_challenge", lambda challenge_id: challenge if challenge_id == "challenge-456" else None)
    monkeypatch.setattr(auth_routes, "consume_auth_challenge", lambda *args, **kwargs: {})
    monkeypatch.setattr(auth_routes, "update_user_auth_state", lambda *args, **kwargs: {})

    client = TestClient(app)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor@example.com", "password": "ValidPassword123!"},
    )
    assert login.status_code == 200
    assert login.json()["status"] == "mfa_required"

    verify = client.post(
        "/api/v1/auth/login/verify",
        json={"email": "doctor@example.com", "code": "654321", "challenge_id": "challenge-456"},
    )
    assert verify.status_code == 200
    assert verify.json()["role"] == "doctor"
    assert verify.json()["access_token"] is None
    assert "careit_access_token" in verify.cookies
    assert "HttpOnly" in verify.headers["set-cookie"]

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "doctor"


def test_rate_limit_middleware_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr("src.api.security.RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr("src.api.security.RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr("src.api.security.RATE_LIMIT_AUTH_MAX_REQUESTS", 2)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/auth/login")
    async def login_probe():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/api/v1/auth/login").status_code == 200
    assert client.get("/api/v1/auth/login").status_code == 200
    blocked = client.get("/api/v1/auth/login")
    assert blocked.status_code == 429
    assert blocked.json()["detail"].lower().startswith("rate limit exceeded")


def test_transcriber_raises_without_provider_outside_demo(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(transcriber, "_transcribe_local_whisper", lambda *args, **kwargs: (_ for _ in ()).throw(ImportError()))

    with pytest.raises(transcriber.TranscriptionError, match="TRANSCRIPTION_PROVIDER_UNAVAILABLE"):
        transcriber.transcribe_audio(b"abc", filename="sample.wav")


def test_external_provider_booking_requires_persisted_doctor(monkeypatch):
    request = appointments_routes.BookingRequest(
        doctor_id="emb:gp01",
        scheduled_at="2026-04-30T10:00:00Z",
    )

    with pytest.raises(appointments_routes.HTTPException, match="persisted provider records"):
        asyncio.run(
            appointments_routes.create_appointment(
                request=request,
                current_user={"user_id": "patient-1", "role": "patient"},
            )
        )


def test_intake_route_denies_cross_doctor_access(monkeypatch):
    monkeypatch.setattr(intake_routes, "get_or_create_doctor_profile", lambda user_id: {"id": "doctor-1"})
    monkeypatch.setattr(intake_routes, "doctor_owns_appointment", lambda doctor_id, appointment_id: False)

    with pytest.raises(intake_routes.HTTPException, match="own appointments"):
        asyncio.run(
            intake_routes.get_intake_form(
                appointment_id="appt-123",
                current_user={"user_id": "doctor-user-1", "role": "doctor"},
            )
        )
