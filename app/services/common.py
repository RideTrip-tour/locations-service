from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.types import ModelT, ParentModelT

logger = logging.getLogger("location_service")

FK_ERROR = "23503"
UNIQUE_ERROR = "23505"


def sql_error_code(exc: IntegrityError) -> str | None:
    return getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)


def integrity_error_to_http(
    exc: IntegrityError,
    *,
    action: str,
    item_name: str,
    base_model: type[ModelT],
    unique_status: int = status.HTTP_400_BAD_REQUEST,
    unique_detail: str | None = None,
    parent_id: int | None = None,
    parent_model: type[ParentModelT] | None = None,
) -> HTTPException:
    code = sql_error_code(exc)
    if code == UNIQUE_ERROR:
        logger.warning(
            "%s %s is failed, %s already exists",
            base_model.__name__,
            action,
            item_name,
        )
        detail = unique_detail or (
            f"{base_model.__name__} with name '{item_name}' already exists"
        )
        return HTTPException(status_code=unique_status, detail=detail)
    if code == FK_ERROR:
        logger.warning(
            "%s %s is failed, parent_id %s not found",
            base_model.__name__,
            action,
            parent_id,
        )
        parent_name = parent_model.__name__ if parent_model else "Parent"
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{parent_name} with id {parent_id} not found",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{base_model.__name__} {action} failed: {exc.orig}",
    )


def map_fk_violation_to_http(exc: IntegrityError, detail: str) -> HTTPException:
    code = sql_error_code(exc)
    if code == FK_ERROR:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=exc.orig,
    )
