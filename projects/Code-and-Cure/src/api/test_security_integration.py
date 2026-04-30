import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_current_user
from src.api.routes import appointments as appointments_routes
from src.api.routes import auth as auth_routes
from src.api.routes import fhir as fhir_routes
from src.api.routes import intake as intake_routes
from src.api.security import RateLimitMiddleware
from src.core_logic import transcriber


def test_legacy_register_endpoint_is_retired():
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "patient@example.com"},
    )

    assert response.status_code == 410
    assert "Clerk-managed authentication" in response.json()["detail"]


def test_me_returns_synced_authenticated_user():
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "user-123",
        "role": "doctor",
        "email": "doctor@example.com",
        "full_name": "Doctor Example",
    }

    client = TestClient(app)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "doctor"
    assert me.json()["email"] == "doctor@example.com"


def test_demo_login_returns_demo_token_and_role(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1/auth")

    monkeypatch.setattr(auth_routes, "ALLOW_DEMO_MODE", True)
    monkeypatch.setattr(
        auth_routes,
        "_ensure_demo_user",
        lambda role: {
            "id": f"{role}-user-1",
            "role": role,
            "email": f"demo.{role}@careit.local",
            "full_name": f"Demo {role.title()}",
        },
    )

    client = TestClient(app)
    response = client.post("/api/v1/auth/demo-login", json={"role": "patient"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "patient"
    assert payload["access_token"]
    assert payload["email"] == "demo.patient@careit.local"


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


def test_transcribe_upload_uses_dedicated_rate_limit(monkeypatch):
    monkeypatch.setattr("src.api.security.RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr("src.api.security.RATE_LIMIT_MAX_REQUESTS", 100)
    monkeypatch.setattr("src.api.security.RATE_LIMIT_AUTH_MAX_REQUESTS", 10)
    monkeypatch.setattr("src.api.security.RATE_LIMIT_TRANSCRIBE_MAX_REQUESTS", 2)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/soap/transcribe-upload")
    async def transcribe_probe():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.post("/api/v1/soap/transcribe-upload").status_code == 200
    assert client.post("/api/v1/soap/transcribe-upload").status_code == 200
    blocked = client.post("/api/v1/soap/transcribe-upload")
    assert blocked.status_code == 429
    assert blocked.json()["detail"].lower().startswith("rate limit exceeded")


def test_transcriber_raises_without_provider_outside_demo(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setattr(transcriber, "_transcribe_local_whisper", lambda *args, **kwargs: (_ for _ in ()).throw(ImportError()))

    with pytest.raises(transcriber.TranscriptionError, match="TRANSCRIPTION_PROVIDER_UNAVAILABLE"):
        transcriber.transcribe_audio(b"abc", filename="sample.wav")


def test_transcriber_prefers_elevenlabs_and_falls_back_to_openai(monkeypatch):
    calls: list[str] = []

    monkeypatch.setenv("ELEVENLABS_API_KEY", "elevenlabs-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setattr(transcriber, "_transcribe_local_whisper", lambda *args, **kwargs: (_ for _ in ()).throw(ImportError()))

    def elevenlabs_success(*args, **kwargs):
        calls.append("elevenlabs")
        return transcriber.TranscriptionResult(
            transcript="hello from elevenlabs",
            provider="elevenlabs_speech_api",
            language_detected="en",
            duration_seconds=1.0,
        )

    def openai_success(*args, **kwargs):
        calls.append("openai")
        return transcriber.TranscriptionResult(
            transcript="hello from openai",
            provider="openai_whisper_api",
            language_detected="en",
            duration_seconds=1.0,
        )

    monkeypatch.setattr(transcriber, "_transcribe_elevenlabs_api", elevenlabs_success)
    monkeypatch.setattr(transcriber, "_transcribe_openai_api", openai_success)

    result = transcriber.transcribe_audio(b"abc", filename="sample.wav")

    assert result.provider == "elevenlabs_speech_api"
    assert calls == ["elevenlabs"]

    calls.clear()

    def elevenlabs_failure(*args, **kwargs):
        calls.append("elevenlabs")
        raise RuntimeError("permission denied")

    monkeypatch.setattr(transcriber, "_transcribe_elevenlabs_api", elevenlabs_failure)

    fallback_result = transcriber.transcribe_audio(b"abc", filename="sample.wav")

    assert fallback_result.provider == "openai_whisper_api"
    assert calls == ["elevenlabs", "openai"]


def test_external_provider_booking_requires_persisted_doctor(monkeypatch):
    request = appointments_routes.BookingRequest(
        doctor_id="emb:gp01",
        scheduled_at="2026-04-30T10:00:00Z",
    )
    monkeypatch.setattr(appointments_routes, "ALLOW_DEMO_MODE", False)

    with pytest.raises(appointments_routes.HTTPException, match="persisted provider records"):
        asyncio.run(
            appointments_routes.create_appointment(
                request=request,
                current_user={"user_id": "patient-1", "role": "patient"},
            )
        )


def test_external_provider_booking_uses_demo_doctor_when_demo_enabled(monkeypatch):
    request = appointments_routes.BookingRequest(
        doctor_id="emb:gp01",
        scheduled_at="2026-04-30T10:00:00Z",
    )

    monkeypatch.setattr(appointments_routes, "ALLOW_DEMO_MODE", True)
    monkeypatch.setattr(
        appointments_routes,
        "get_or_create_any_doctor",
        lambda: {"id": "doctor-demo-1"},
    )
    monkeypatch.setattr(
        appointments_routes,
        "insert_appointment",
        lambda patient_id, doctor_id, scheduled_at: {
            "id": "appt-1",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": scheduled_at,
            "status": "pending",
        },
    )

    result = asyncio.run(
        appointments_routes.create_appointment(
            request=request,
            current_user={"user_id": "patient-1", "role": "patient"},
        )
    )

    assert result["booking"]["doctor_id"] == "doctor-demo-1"


def test_doctor_portal_lists_all_appointments_in_demo_mode(monkeypatch):
    monkeypatch.setattr(appointments_routes, "ALLOW_DEMO_MODE", True)
    monkeypatch.setattr(
        appointments_routes,
        "get_all_appointments",
        lambda: [{"id": "appt-1"}, {"id": "appt-2"}, {"id": "appt-3"}],
    )

    result = asyncio.run(
        appointments_routes.get_appointments(
            current_user={"user_id": "doctor-user-1", "role": "doctor"},
        )
    )

    assert len(result) == 3


def test_intake_route_denies_cross_doctor_access(monkeypatch):
    monkeypatch.setattr(intake_routes, "ALLOW_DEMO_MODE", False)
    monkeypatch.setattr(intake_routes, "get_or_create_doctor_profile", lambda user_id: {"id": "doctor-1"})
    monkeypatch.setattr(intake_routes, "doctor_owns_appointment", lambda doctor_id, appointment_id: False)

    with pytest.raises(intake_routes.HTTPException, match="own appointments"):
        asyncio.run(
            intake_routes.get_intake_form(
                appointment_id="appt-123",
                current_user={"user_id": "doctor-user-1", "role": "doctor"},
            )
        )


def test_fhir_export_denies_cross_doctor_access_outside_demo(monkeypatch):
    monkeypatch.setattr(fhir_routes, "ALLOW_DEMO_MODE", False)
    monkeypatch.setattr(fhir_routes, "get_or_create_doctor_profile", lambda user_id: {"id": "doctor-1"})
    monkeypatch.setattr(fhir_routes, "doctor_owns_appointment", lambda doctor_id, appointment_id: False)

    with pytest.raises(fhir_routes.HTTPException, match="own appointments"):
        asyncio.run(
            fhir_routes.export_to_emr(
                appointment_id="appt-123",
                current_user={"user_id": "doctor-user-1", "role": "doctor"},
            )
        )


def test_fhir_export_allows_cross_doctor_access_in_demo_mode(monkeypatch):
    monkeypatch.setattr(fhir_routes, "ALLOW_DEMO_MODE", True)
    monkeypatch.setattr(fhir_routes, "get_or_create_doctor_profile", lambda user_id: {"id": "doctor-1"})
    monkeypatch.setattr(fhir_routes, "doctor_owns_appointment", lambda doctor_id, appointment_id: False)
    monkeypatch.setattr(
        fhir_routes,
        "get_soap_note_by_appointment",
        lambda appointment_id: {
            "id": "soap-1",
            "doctor_id": "doctor-demo-1",
            "subjective": "Subjective",
            "objective": "Objective",
            "assessment": "Assessment",
            "plan": "Plan",
            "approved": True,
        },
    )
    monkeypatch.setattr(
        fhir_routes,
        "get_appointment",
        lambda appointment_id: {"id": appointment_id, "patient_id": "patient-1"},
    )
    monkeypatch.setattr(
        fhir_routes,
        "build_fhir_bundle",
        lambda **kwargs: type("Result", (), {"bundle": {"resourceType": "Bundle", "entry": []}})(),
    )
    monkeypatch.setattr(fhir_routes, "insert_fhir_record", lambda **kwargs: None)

    result = asyncio.run(
        fhir_routes.export_to_emr(
            appointment_id="appt-123",
            current_user={"user_id": "doctor-user-1", "role": "doctor"},
        )
    )

    assert result.status == "success"
