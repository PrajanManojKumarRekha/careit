import os
from pathlib import Path

from dotenv import load_dotenv


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _raw_env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_initial_app_env = os.getenv("APP_ENV", "development").strip().lower()
_initial_is_production = _initial_app_env == "production"
_initial_allow_dotenv = _raw_env_flag("ALLOW_DOTENV", default=not _initial_is_production)
_project_root = Path(__file__).resolve().parents[2]
_env_path = _project_root / ".env"

if _initial_allow_dotenv:
    load_dotenv(_env_path)

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"

ALLOW_DEMO_MODE = _env_flag("ALLOW_DEMO_MODE", default=not IS_PRODUCTION)
ALLOW_DOTENV = _env_flag("ALLOW_DOTENV", default=not IS_PRODUCTION)
ALLOW_ONEDRIVE_DOTENV = _env_flag("ALLOW_ONEDRIVE_DOTENV", default=False)
AUTH_RETURN_TOKEN_IN_BODY = _env_flag("AUTH_RETURN_TOKEN_IN_BODY", default=False)

CORS_ORIGINS = _env_list(
    "CORS_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)

ALLOWED_HOSTS = _env_list(
    "ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "*.vercel.app"],
)

JWT_COOKIE_NAME = os.getenv("JWT_COOKIE_NAME", "careit_access_token")
JWT_COOKIE_SECURE = _env_flag("JWT_COOKIE_SECURE", default=IS_PRODUCTION)
JWT_COOKIE_SAMESITE = os.getenv(
    "JWT_COOKIE_SAMESITE",
    "none" if IS_PRODUCTION else "lax",
).strip().lower()
JWT_COOKIE_MAX_AGE_SECONDS = int(os.getenv("JWT_COOKIE_MAX_AGE_SECONDS", str(24 * 60 * 60)))

AUTH_CODE_TTL_MINUTES = int(os.getenv("AUTH_CODE_TTL_MINUTES", "10"))
AUTH_LOCKOUT_THRESHOLD = int(os.getenv("AUTH_LOCKOUT_THRESHOLD", "5"))
AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))
AUTH_EMAIL_DELIVERY_MODE = os.getenv(
    "AUTH_EMAIL_DELIVERY_MODE",
    "smtp" if IS_PRODUCTION else "console",
).strip().lower()
AUTH_EMAIL_FROM = os.getenv("AUTH_EMAIL_FROM", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = _env_flag("SMTP_USE_TLS", default=True)
SMTP_USE_SSL = _env_flag("SMTP_USE_SSL", default=False)

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "").strip()
CLERK_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "").strip()
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "").strip()
CLERK_JWT_ISSUER = os.getenv("CLERK_JWT_ISSUER", "").strip()
CLERK_JWT_AUDIENCE = os.getenv("CLERK_JWT_AUDIENCE", "").strip()
CLERK_API_URL = os.getenv("CLERK_API_URL", "https://api.clerk.com").strip()
CLERK_TOKEN_TEMPLATE = os.getenv("CLERK_TOKEN_TEMPLATE", "careit-api").strip() or "careit-api"

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
RATE_LIMIT_AUTH_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_AUTH_MAX_REQUESTS", "10"))
RATE_LIMIT_TRANSCRIBE_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_TRANSCRIBE_MAX_REQUESTS", "5"))
TRANSCRIPTION_MAX_CONCURRENCY = int(os.getenv("TRANSCRIPTION_MAX_CONCURRENCY", "2"))
TRANSCRIPTION_QUEUE_TIMEOUT_SECONDS = float(os.getenv("TRANSCRIPTION_QUEUE_TIMEOUT_SECONDS", "1.5"))
