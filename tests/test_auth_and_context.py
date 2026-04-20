from types import SimpleNamespace
from pathlib import Path
import sys

import asyncio

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dependencies.auth import get_current_user_id, get_optional_current_user_id # noqa E402
from app.middlerware.request_context import user_context_middleware # noqa E402


def make_request(*, user=None, headers=None):
    return SimpleNamespace(
        state=SimpleNamespace(user=user),
        headers=headers or {},
    )


def test_get_current_user_id_reads_state_sub():
    request = make_request(user={"sub": "7"})

    assert get_current_user_id(request) == 7


def test_get_current_user_id_reads_x_user_id_header():
    request = make_request(user=None, headers={"x-user-id": "7"})

    assert get_current_user_id(request) == 7


def test_get_optional_current_user_id_returns_none():
    request = make_request(user=None)

    assert get_optional_current_user_id(request) is None


def test_get_current_user_id_rejects_invalid_payload():
    request = make_request(user={"sub": "abc"})

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(request)

    assert exc_info.value.status_code == 401


def test_user_context_middleware_restores_claims():
    request = make_request(user=None, headers={})
    request.headers["x-user-claims"] = "eyJzdWIiOiA3fQ"

    async def call_next(req):
        return req.state.user

    result = asyncio.run(user_context_middleware(request, call_next))

    assert result == {"sub": 7}
