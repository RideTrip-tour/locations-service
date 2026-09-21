from typing import Annotated, Any

from fastapi import Depends, HTTPException, Path, Query, status
from pydantic import BeforeValidator

from app.services.locations import LocationService, get_location_service
from app.services.references import ReferenceService, get_reference_service

MAX_INT32 = 2_147_483_647


def _split_query_values(
    values: list[str] | None, *, max_length: int | None = None
) -> list[str] | None:
    """Normalize repeated and comma-separated query values into one validated list."""
    if not values:
        return None

    result: list[str] = []
    for value in values:
        for part in value.split(","):
            normalized = part.strip()
            if not normalized:
                continue
            if max_length is not None and len(normalized) > max_length:
                raise HTTPException(
                    status_code=422,
                    detail=f"filter value must contain at most {max_length} characters",
                )
            result.append(normalized)
    return result or None


def _parse_int_ids(values: Any, *, field_name: str = "id") -> list[int] | None:
    """Parse repeated and comma-separated integer ids from query parameters."""
    if values is not None and not isinstance(values, list):
        values = [values]

    raw_values = _split_query_values(
        [str(value) for value in values] if values is not None else None
    )
    if raw_values is None:
        return None

    ids: list[int] = []
    for value in raw_values:
        try:
            id_value = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer") from exc
        if id_value < 1:
            raise ValueError(f"{field_name} must be greater than or equal to 1")
        if id_value > MAX_INT32:
            continue
        ids.append(id_value)
    return ids


def _parse_location_id(location_id: Annotated[str, Path()]) -> int:
    try:
        parsed_location_id = int(location_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="location_id must be an integer",
        ) from exc
    if parsed_location_id < 1 or parsed_location_id > MAX_INT32:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location not found"
        )
    return parsed_location_id


ActivityIdQuery = Annotated[
    list[int] | None,
    BeforeValidator(_parse_int_ids),
    Query(
        description="Activity ids. Supports repeated values and CSV, e.g. activity_id=1&activity_id=2 or 1,2."
    ),
]
LocationIdPath = Annotated[int, Depends(_parse_location_id)]
SearchQuery = Annotated[str | None, Query(max_length=255)]
ReferenceNameQuery = Annotated[str | None, Query(min_length=3, max_length=150)]
ReferenceIdQuery = Annotated[
    list[int] | None,
    BeforeValidator(_parse_int_ids),
    Query(
        description="Reference ids. Supports repeated values and CSV, e.g. activity_id=1&activity_id=2 or 1,2."
    ),
]
StringListQuery = Annotated[list[str] | None, Query()]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
LocationServiceDep = Annotated[LocationService, Depends(get_location_service)]
ReferenceServiceDep = Annotated[ReferenceService, Depends(get_reference_service)]
