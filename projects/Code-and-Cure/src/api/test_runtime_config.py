from src.api import config


def test_validate_runtime_config_requires_secure_none_cookie(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    monkeypatch.setattr(config, "JWT_COOKIE_SAMESITE", "none")
    monkeypatch.setattr(config, "JWT_COOKIE_SECURE", False)

    try:
        config.validate_runtime_config()
        assert False, "Expected validate_runtime_config to fail for insecure SameSite=None cookie."
    except RuntimeError as exc:
        assert "JWT_COOKIE_SECURE" in str(exc)


def test_validate_runtime_config_requires_clerk_settings_in_production(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(config, "JWT_COOKIE_SAMESITE", "none")
    monkeypatch.setattr(config, "JWT_COOKIE_SECURE", True)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["https://careit-web.vercel.app"])
    monkeypatch.setattr(config, "CORS_ORIGIN_REGEX", None)
    monkeypatch.setattr(config, "ALLOWED_HOSTS", ["careit-api.onrender.com"])
    monkeypatch.setattr(config, "CLERK_SECRET_KEY", "")
    monkeypatch.setattr(config, "CLERK_JWKS_URL", "")
    monkeypatch.setattr(config, "CLERK_JWT_ISSUER", "")
    monkeypatch.setenv("SUPABASE_URL", "https://prod.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "prod-key")

    try:
        config.validate_runtime_config()
        assert False, "Expected validate_runtime_config to fail without Clerk configuration."
    except RuntimeError as exc:
        assert "CLERK_SECRET_KEY" in str(exc)
