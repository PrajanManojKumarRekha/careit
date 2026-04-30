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


def _looks_placeholder(value: str) -> bool:
    cleaned = value.strip().lower()
    if not cleaned:
        return True
    placeholder_tokens = (
        "replace-with",
        "replace_me",
        "your-project",
        "your-clerk-domain",
        "your-api.example.com",
        "example.com",
    )
    return any(token in cleaned for token in placeholder_tokens)


def _all_local_hosts(values: list[str]) -> bool:
    if not values:
        return False
    local_tokens = ("localhost", "127.0.0.1")
    return all(any(token in value.lower() for token in local_tokens) for value in values)


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
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None

ALLOWED_HOSTS = _env_list(
    "ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "*.vercel.app"],
)

_configured_jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
JWT_SECRET_KEY = _configured_jwt_secret or (
    "careit-demo-dev-secret" if ALLOW_DEMO_MODE and not IS_PRODUCTION else ""
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


def validate_runtime_config() -> None:
    if JWT_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        raise RuntimeError("JWT_COOKIE_SAMESITE must be one of: lax, strict, none.")
    if JWT_COOKIE_SAMESITE == "none" and not JWT_COOKIE_SECURE:
        raise RuntimeError("JWT_COOKIE_SECURE must be true when JWT_COOKIE_SAMESITE is 'none'.")

    if not IS_PRODUCTION:
        return

    production_errors: list[str] = []

    required_env = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", "").strip(),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", "").strip(),
        "CLERK_SECRET_KEY": CLERK_SECRET_KEY,
        "CLERK_JWKS_URL": CLERK_JWKS_URL,
        "CLERK_JWT_ISSUER": CLERK_JWT_ISSUER,
    }
    if ALLOW_DEMO_MODE:
        required_env["JWT_SECRET_KEY"] = _configured_jwt_secret

    for name, value in required_env.items():
        if _looks_placeholder(value):
            production_errors.append(f"{name} must be set to a real production value.")

    if not CORS_ORIGINS and not CORS_ORIGIN_REGEX:
        production_errors.append("Set CORS_ORIGINS and/or CORS_ORIGIN_REGEX for production.")
    if CORS_ORIGINS and _all_local_hosts(CORS_ORIGINS) and not CORS_ORIGIN_REGEX:
        production_errors.append(
            "CORS_ORIGINS only contains localhost/127.0.0.1 values. Add your Vercel domain or CORS_ORIGIN_REGEX."
        )
    if not ALLOWED_HOSTS or _all_local_hosts(ALLOWED_HOSTS):
        production_errors.append("ALLOWED_HOSTS must include your Render hostname and any custom API domain.")

    if production_errors:
        raise RuntimeError("Invalid production configuration: " + " ".join(production_errors))
