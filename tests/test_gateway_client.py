from __future__ import annotations

import time

import httpx
import jwt
import pytest

from app.client.gateway_client import GatewayClient
from app.exceptions import UserContextIncompleteError, UserContextMissingError
from app.middlerware.context import user_claims


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
        jwt_algorithm = "HS256"
        access_token_expire_sec = 3600

    monkeypatch.setattr(gc_module, "settings", FakeSettings)
    return FakeSettings


@pytest.fixture
def user_ctx():
    token = user_claims.set({"id": 42, "is_active": True, "is_superuser": False})
    yield
    user_claims.reset(token)


def test_gateway_client_is_singleton():
    assert GatewayClient() is GatewayClient()


def test_gateway_client_reuses_http_client(settings_patch):
    first = GatewayClient()
    second = GatewayClient()
    assert first.client is second.client


def test_get_user_context_raises_when_missing(settings_patch):
    client = GatewayClient()
    client.client = httpx.AsyncClient(base_url="http://test")

    with pytest.raises(UserContextMissingError):
        client._get_user_context()


def test_get_user_context_raises_when_incomplete(settings_patch):
    client = GatewayClient()
    client.client = httpx.AsyncClient(base_url="http://test")

    token = user_claims.set({"id": 42})
    try:
        with pytest.raises(UserContextIncompleteError):
            client._get_user_context()
    finally:
        user_claims.reset(token)


def test_get_user_context_encodes_claims(settings_patch, user_ctx):
    client = GatewayClient()
    client.client = httpx.AsyncClient(base_url="http://test")

    encoded = client._get_user_context()
    decoded = jwt.decode(
        encoded,
        settings_patch.jwt_secret,
        algorithms=[settings_patch.jwt_algorithm],
        audience=settings_patch.gateway_name,
    )

    assert decoded["sub"] == "42"
    assert decoded["is_active"] is True
    assert decoded["is_superuser"] is False
    assert decoded["aud"] == settings_patch.gateway_name
    assert (
        decoded["exp"] > int(time.time()) + settings_patch.access_token_expire_sec - 10
    )


def test_get_headers_includes_service_and_user(settings_patch, user_ctx):
    client = GatewayClient()
    client.client = httpx.AsyncClient(base_url="http://test")

    headers = client._get_headers()

    assert headers["X-Service-ID"] == "locations-service"
    assert headers["X-Service-Token"] == "secret-token"
    assert "X-User-Context" in headers
    jwt.decode(
        headers["X-User-Context"],
        settings_patch.jwt_secret,
        algorithms=[settings_patch.jwt_algorithm],
        audience=settings_patch.gateway_name,
    )


@pytest.mark.asyncio
async def test_request_returns_response_on_success(settings_patch, user_ctx):
    client = GatewayClient()

    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    client.client = httpx.AsyncClient(
        base_url="http://gateway.test", transport=httpx.MockTransport(handler)
    )

    response = await client._request("GET", "/api/locations", params={"limit": 10})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured["method"] == "GET"
    assert captured["path"] == "/api/locations"
    assert captured["params"] == {"limit": "10"}
    assert captured["headers"]["x-service-id"] == "locations-service"
    assert captured["headers"]["x-service-token"] == "secret-token"
    assert "x-user-context" in captured["headers"]

    await client.client.aclose()


@pytest.mark.asyncio
async def test_request_raises_on_4xx(settings_patch, user_ctx):
    client = GatewayClient()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client.client = httpx.AsyncClient(
        base_url="http://gateway.test", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client._request("GET", "/api/missing")

    assert exc_info.value.response.status_code == 404

    await client.client.aclose()


@pytest.mark.asyncio
async def test_request_raises_on_5xx(settings_patch, user_ctx):
    client = GatewayClient()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client.client = httpx.AsyncClient(
        base_url="http://gateway.test", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("POST", "/api/anything")

    await client.client.aclose()


@pytest.mark.asyncio
async def test_request_logs_and_reraises_transport_error(
    settings_patch, user_ctx, caplog
):
    client = GatewayClient()

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client.client = httpx.AsyncClient(
        base_url="http://gateway.test", transport=httpx.MockTransport(handler)
    )

    with (
        caplog.at_level("ERROR", logger="location_service"),
        pytest.raises(httpx.ConnectError),
    ):
        await client._request("GET", "/api/locations")

    assert any("Gateway request failed" in rec.message for rec in caplog.records)

    await client.client.aclose()


@pytest.mark.asyncio
async def test_request_propagates_user_context_missing(settings_patch):
    client = GatewayClient()
    client.client = httpx.AsyncClient(base_url="http://test")

    with pytest.raises(UserContextMissingError):
        await client._request("GET", "/api/locations")

    await client.client.aclose()


@pytest.mark.asyncio
async def test_close_calls_aclose(settings_patch):
    client = GatewayClient()
    closed = {"called": False}

    class FakeAsyncClient:
        async def aclose(self):
            closed["called"] = True

    client.client = FakeAsyncClient()

    await client.close()

    assert closed["called"] is True
