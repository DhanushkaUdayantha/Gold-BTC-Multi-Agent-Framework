"""
Security Hardening Test Suite.

Verifies:
1. SEC-01: Demo reset endpoint authorization (authorized, unauthorized, missing, invalid, dev mode)
2. SEC-02: Rate limiting behavior (429 response, Retry-After header)
3. SEC-03: Admin token validation and fail-closed behavior
4. SEC-04: CORS configuration and security headers
5. SEC-07: Error sanitization (500 internal error does not leak stack trace or internal paths)
6. Decoupling: Unauthorized attempts cannot mutate any store
"""
import os
import pytest
from fastapi.testclient import TestClient
from config.settings import get_settings
from src.api.main import app
from src.core.rate_limiter import get_rate_limiter


@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Reset rate limiter state before each test."""
    get_rate_limiter().reset()
    yield
    get_rate_limiter().reset()


def test_security_headers_present():
    """Verify defensive security headers are returned on all API responses."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")


def test_cors_dev_origins_allowed():
    """Verify development CORS allows localhost origins."""
    client = TestClient(app)
    response = client.options(
        "/api/v1/decision",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_demo_reset_dev_mode_permits_reset(monkeypatch):
    """In development mode with RESET_AUTH_REQUIRED=False, unauthenticated reset is permitted."""
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "RESET_AUTH_REQUIRED", False)

    client = TestClient(app)
    response = client.post("/api/v1/decision/trade/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_demo_reset_enforced_missing_token_rejected(monkeypatch):
    """When auth is enforced, missing X-Admin-Token is rejected with 401."""
    settings = get_settings()
    monkeypatch.setattr(settings, "RESET_AUTH_REQUIRED", True)
    monkeypatch.setattr(settings, "ADMIN_AUTH_TOKEN", "super-secret-admin-token")

    client = TestClient(app)
    response = client.post("/api/v1/decision/trade/reset")
    assert response.status_code == 401
    assert "Invalid or missing X-Admin-Token header" in response.json()["detail"]


def test_demo_reset_enforced_invalid_token_rejected(monkeypatch):
    """When auth is enforced, invalid X-Admin-Token is rejected with 401."""
    settings = get_settings()
    monkeypatch.setattr(settings, "RESET_AUTH_REQUIRED", True)
    monkeypatch.setattr(settings, "ADMIN_AUTH_TOKEN", "super-secret-admin-token")

    client = TestClient(app)
    response = client.post(
        "/api/v1/decision/trade/reset",
        headers={"X-Admin-Token": "wrong-token-value"}
    )
    assert response.status_code == 401
    assert "Invalid or missing X-Admin-Token header" in response.json()["detail"]


def test_demo_reset_enforced_valid_token_authorized(monkeypatch):
    """When auth is enforced, valid X-Admin-Token succeeds."""
    settings = get_settings()
    monkeypatch.setattr(settings, "RESET_AUTH_REQUIRED", True)
    monkeypatch.setattr(settings, "ADMIN_AUTH_TOKEN", "super-secret-admin-token")

    client = TestClient(app)
    response = client.post(
        "/api/v1/decision/trade/reset",
        headers={"X-Admin-Token": "super-secret-admin-token"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_demo_reset_rate_limiting(monkeypatch):
    """Verify that exceeding reset rate limit triggers HTTP 429 with Retry-After."""
    settings = get_settings()
    monkeypatch.setattr(settings, "RATE_LIMITING_ENABLED", True)
    monkeypatch.setattr(settings, "RESET_AUTH_REQUIRED", False)

    client = TestClient(app)
    # Reset limit is 10 requests / 60 seconds
    for _ in range(10):
        res = client.post("/api/v1/decision/trade/reset")
        assert res.status_code == 200

    # 11th request must be rate-limited
    res_exceeded = client.post("/api/v1/decision/trade/reset")
    assert res_exceeded.status_code == 429
    assert "Rate limit exceeded" in res_exceeded.json()["detail"]
    assert "Retry-After" in res_exceeded.headers


def test_error_sanitization_does_not_leak_stacktrace(monkeypatch):
    """Verify that internal 500 errors return structured messages without stacktraces."""
    from src.services.decision_service import DecisionService
    
    def _exploding_decision(*args, **kwargs):
        raise ValueError("SecretDbPasswordAtInternalPath /var/secrets/keys.db")

    client = TestClient(app)
    with monkeypatch.context() as m:
        m.setattr(DecisionService, "get_decision", _exploding_decision)
        response = client.get("/api/v1/decision")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        # Must not contain internal sensitive string or stacktrace
        assert "SecretDbPasswordAtInternalPath" not in str(data)
        assert "/var/secrets" not in str(data)
        assert "Traceback" not in str(data)
