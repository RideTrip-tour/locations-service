from fastapi import HTTPException, Request, status


def _extract_user_id(request: Request) -> int | None:
    user = getattr(request.state, "user", None)

    if isinstance(user, dict):
        user_id = user.get("sub") or user.get("user_id") or user.get("id")
        if user_id not in (None, ""):
            try:
                return int(user_id)
            except (TypeError, ValueError):
                return None

    header_user_id = request.headers.get("x-user-id")
    if header_user_id not in (None, ""):
        try:
            return int(header_user_id)
        except (TypeError, ValueError):
            return None

    return None


def get_current_user_id(request: Request) -> int:
    user_id = _extract_user_id(request)
    if user_id is not None:
        return user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )


def get_optional_current_user_id(request: Request) -> int | None:
    return _extract_user_id(request)
