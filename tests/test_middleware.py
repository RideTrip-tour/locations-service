import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.middlerware.request_context import user_context_middleware


def create_request(headers=None):
    request = SimpleNamespace()
    request.headers = headers or {}
    request.state = SimpleNamespace()
    return request


@pytest.mark.asyncio
async def test_middleware_with_valid_claims():
    request = create_request(
        {
            "x-user-claims": base64.urlsafe_b64encode(
                json.dumps({"user_id": 123}).encode()
            ).decode()
        }
    )

    call_next = AsyncMock(return_value={"status": "ok"})

    await user_context_middleware(request, call_next)

    assert request.state.user == {"user_id": 123}
    assert request.state.user_id == 123
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_with_user_id():
    request = create_request({"x-user-id": "456"})

    call_next = AsyncMock(return_value={"status": "ok"})

    await user_context_middleware(request, call_next)

    assert request.state.user == {"sub": "456", "user_id": 456}
    assert request.state.user_id == 456
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_no_headers():
    request = create_request({})

    call_next = AsyncMock(return_value={"status": "ok"})

    await user_context_middleware(request, call_next)

    assert request.state.user == {}
    assert not hasattr(request.state, "user_id")
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_invalid_claims():
    request = create_request({"x-user-claims": "invalid!!!"})

    call_next = AsyncMock()

    response = await user_context_middleware(request, call_next)

    assert response.status_code == 401
    assert response.body == b'{"detail":"Unauthorized"}'
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_claims_priority():
    request = create_request(
        {
            "x-user-claims": base64.urlsafe_b64encode(
                json.dumps({"user_id": 999}).encode()
            ).decode(),
            "x-user-id": "123",
        }
    )

    call_next = AsyncMock(return_value={"status": "ok"})

    await user_context_middleware(request, call_next)

    assert request.state.user_id == 999
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_user_already_in_state():
    """Тест, когда пользователь уже есть в state."""
    request = create_request({"x-user-claims": "some_claims"})
    request.state.user = {"pre_existing": True}

    call_next = AsyncMock(return_value={"status": "ok"})

    await user_context_middleware(request, call_next)

    assert request.state.user == {"pre_existing": True}
    call_next.assert_called_once_with(request)
