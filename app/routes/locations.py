from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.auth import get_current_user_id, get_optional_current_user_id
from app.routes.query_params import (
    ActivityIdQuery,
    LimitQuery,
    LocationIdPath,
    LocationServiceDep,
    OffsetQuery,
    SearchQuery,
    StringListQuery,
    _split_query_values,
)
from app.schemas.locations import (
    FavoriteStateResponse,
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)

router = APIRouter(prefix="/api/locations", tags=["locations"])
OptionalUserId = Annotated[int | None, Depends(get_optional_current_user_id)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]


@router.get("", response_model=LocationListResponse)
async def read_locations(
    user_id: OptionalUserId,
    service: LocationServiceDep,
    search: SearchQuery = None,
    region: StringListQuery = None,
    city: StringListQuery = None,
    country: StringListQuery = None,
    activity_id: ActivityIdQuery = None,
    styles: StringListQuery = None,
    levels: StringListQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Return locations using multi-value filters with OR inside each field."""
    return await service.list_locations(
        search=search,
        region=_split_query_values(region, max_length=255),
        city=_split_query_values(city, max_length=255),
        country=_split_query_values(country, max_length=120),
        activity_id=activity_id,
        styles=_split_query_values(styles, max_length=120),
        levels=_split_query_values(levels, max_length=120),
        limit=limit,
        offset=offset,
        user_id=user_id,
    )


@router.get("/filters", response_model=LocationFilterOptions)
async def read_location_filters(
    service: LocationServiceDep,
):
    return await service.list_filter_options()


@router.get("/favorites", response_model=LocationListResponse)
async def read_favorite_locations(
    user_id: CurrentUserId,
    service: LocationServiceDep,
    search: SearchQuery = None,
    region: StringListQuery = None,
    city: StringListQuery = None,
    country: StringListQuery = None,
    activity_id: ActivityIdQuery = None,
    styles: StringListQuery = None,
    levels: StringListQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Return current user's favorite locations using the same filters as the public list."""
    return await service.list_favorites(
        user_id=user_id,
        search=search,
        region=_split_query_values(region, max_length=255),
        city=_split_query_values(city, max_length=255),
        country=_split_query_values(country, max_length=120),
        activity_id=activity_id,
        styles=_split_query_values(styles, max_length=120),
        levels=_split_query_values(levels, max_length=120),
        is_active=True,
        limit=limit,
        offset=offset,
    )


@router.get("/{location_id}", response_model=LocationRead)
async def read_location(
    location_id: LocationIdPath,
    user_id: OptionalUserId,
    service: LocationServiceDep,
):
    return await service.get_location(location_id, user_id=user_id)


@router.post("/{location_id}/favorite", response_model=FavoriteStateResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite_location(
    location_id: LocationIdPath,
    user_id: CurrentUserId,
    service: LocationServiceDep,
):
    return await service.add_favorite(location_id, user_id)


@router.delete("/{location_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_location(
    location_id: LocationIdPath,
    user_id: CurrentUserId,
    service: LocationServiceDep,
):
    await service.remove_favorite(location_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
