import time

import jwt
import pytest
from internal_middleware import user_claims

from app.client.gateway_client import GatewayClient


@pytest.fixture(autouse=True)
def reset_singleton():
    GatewayClient._instance = None
    yield
    GatewayClient._instance = None


@pytest.fixture
def settings_patch(monkeypatch):
    from app.client import gateway_client as gc_module

    class FakeSettings:
        gateway_url = "http://gateway.test"
        service_id = "locations-service"
        service_token = "secret-token"
        gateway_name = "gateway"
        jwt_secret = "test-secret"
        access_token_expire_sec = 3600

    monkeypatch.setattr(gc_module, "settings", FakeSettings)
    return FakeSettings


@pytest.fixture
def user_ctx():
    token = user_claims.set({"id": 42, "is_active": True, "is_superuser": False})
    yield
    user_claims.reset(token)


def test_init_passes_settings_to_parent(settings_patch):
    client = GatewayClient()

    assert client.base_url == "http://gateway.test"
    assert client.service_id == "locations-service"
    assert client.service_token == "secret-token"
    assert client.gateway_name == "gateway"
    assert client.access_token_expire_sec == 3600
    assert client.jwt_secret == "test-secret"


def test_get_user_context_returns_jwt(settings_patch, user_ctx):
    client = GatewayClient()

    encoded = client._get_user_context()
    decoded = jwt.decode(
        encoded,
        settings_patch.jwt_secret,
        algorithms=["HS256"],
        audience=settings_patch.gateway_name,
    )

    assert decoded["sub"] == "42"
    assert decoded["is_active"] is True
    assert decoded["is_superuser"] is False
    assert decoded["aud"] == "gateway"
    assert decoded["exp"] > int(time.time())


def test_get_user_context_raises_when_claims_missing(settings_patch):
    client = GatewayClient()

    with pytest.raises(ValueError, match="User claims are not available"):
        client._get_user_context()


def test_get_user_context_raises_when_claims_incomplete(settings_patch):
    client = GatewayClient()
    token = user_claims.set({"id": 42})
    try:
        with pytest.raises(ValueError, match="Required user claims are missing"):
            client._get_user_context()
    finally:
        user_claims.reset(token)
