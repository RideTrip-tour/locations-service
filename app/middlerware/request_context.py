import base64
import json
import logging

from fastapi import HTTPException, Request, status

logger = logging.getLogger("location_service")


def _urlsafe_b64decode_padded(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


async def user_context_middleware(request: Request, call_next):
    if getattr(request.state, "user", None) is None:
        claims_header = request.headers.get("x-user-claims")
        user_id_header = request.headers.get("x-user-id")

        if claims_header:
            try:
                raw = _urlsafe_b64decode_padded(claims_header)
                user = json.loads(raw.decode("utf-8"))
                if not isinstance(user, dict):
                    raise ValueError("X-User-Claims must be a JSON object")
                request.state.user = user
            except Exception:
                logger.warning("Invalid X-User-Claims header", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )
        elif user_id_header:
            request.state.user = {"sub": user_id_header}

    return await call_next(request)
