import base64
import json
import logging
import re

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("location_service")


def _urlsafe_b64decode_padded(value: str) -> bytes:
    if not value:
        raise ValueError("Empty claims value")
    if not isinstance(value, str):
        raise TypeError("Claims must be a string")
    if not re.match(r"^[A-Za-z0-9\-_]*={0,2}$", value):
        raise ValueError("Invalid characters in base64 string")
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except ValueError:
        raise ValueError("Invalid baase64 encoding")


def _extract_user_id(user_data: dict) -> int | str | None:
    """Extract user_id from user_data."""
    user_id = user_data.get("user_id") or user_data.get("sub") or user_data.get("id")
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return str(user_id)


def _process_claims(claims_header: str, request: Request):
    """Process X-User-Claims header."""
    if not claims_header or claims_header.strip() == "":
        raise ValueError("Empty claims header")
    raw = _urlsafe_b64decode_padded(claims_header)
    user_data = json.loads(raw.decode("utf-8"))
    if not isinstance(user_data, dict):
        raise TypeError("X-User-Claims must be a JSON object")
    request.state.user = user_data
    user_id = _extract_user_id(user_data)
    if user_id is not None:
        request.state.user_id = user_id
    logger.debug(f"User data loaded from claims: {list(user_data.keys())}")


def _process_user_id(user_id_header: str, request: Request):
    """Process X-User-ID header."""
    try:
        user_id_int = int(user_id_header)
        request.state.user = {"sub": str(user_id_int), "user_id": user_id_int}
        request.state.user_id = user_id_int
        logger.debug(f"User ID loaded from header: {user_id_int}")
    except (TypeError, ValueError):
        request.state.user = {"sub": user_id_header, "user_id": user_id_header}
        request.state.user_id = user_id_header
        logger.debug(f"User ID (string) loaded from header: {user_id_header}")


async def user_context_middleware(request: Request, call_next):
    if getattr(request.state, "user", None) is None:
        claims_header = request.headers.get("x-user-claims")
        user_id_header = request.headers.get("x-user-id")
        try:
            if claims_header is not None:
                _process_claims(claims_header, request)
            elif user_id_header is not None:
                _process_user_id(user_id_header, request)
            else:
                request.state.user = {}
                logger.debug("No user context found in request")
        except ValueError as e:
            logger.warning(f"Invalid X-User-Claims header: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized"},
            )

    return await call_next(request)
