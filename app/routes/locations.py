from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies.auth import get_current_user_id, get_optional_current_user_id
from app.schemas.locations import (
    FavoriteStateResponse,
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)
from app.services.locations import LocationService, get_location_service

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=LocationListResponse)
async def read_locations(
    search: str | None = Query(default=None, max_length=255),
    region: str | None = Query(default=None, max_length=255),
    city: str | None = Query(default=None, max_length=255),
    country: str | None = Query(default=None, max_length=120),
    activity_id: int | None = Query(default=None, ge=1),
    style: str | None = Query(default=None, max_length=120),
    level: str | None = Query(default=None, max_length=120),
    is_active: bool | None = True,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int | None = Depends(get_optional_current_user_id),
    service: LocationService = Depends(get_location_service),
):
    return await service.list_locations(
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        style=style,
        level=level,
        is_active=is_active,
        limit=limit,
        offset=offset,
        user_id=user_id,
    )


@router.get("/filters", response_model=LocationFilterOptions)
async def read_location_filters(
    service: LocationService = Depends(get_location_service),
):
    return await service.list_filter_options()


@router.get("/favorites", response_model=LocationListResponse)
async def read_favorite_locations(
    search: str | None = Query(default=None, max_length=255),
    region: str | None = Query(default=None, max_length=255),
    city: str | None = Query(default=None, max_length=255),
    country: str | None = Query(default=None, max_length=120),
    activity_id: int | None = Query(default=None, ge=1),
    style: str | None = Query(default=None, max_length=120),
    level: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_active: bool | None = True,
    user_id: int = Depends(get_current_user_id),
    service: LocationService = Depends(get_location_service),
):
    return await service.list_favorites(
        user_id=user_id,
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        style=style,
        level=level,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.get("/{location_id}", response_model=LocationRead)
async def read_location(
    location_id: int,
    user_id: int | None = Depends(get_optional_current_user_id),
    service: LocationService = Depends(get_location_service),
):
    return await service.get_location(location_id, user_id=user_id)


@router.post("/{location_id}/favorite", response_model=FavoriteStateResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite_location(
    location_id: int,
    user_id: int = Depends(get_current_user_id),
    service: LocationService = Depends(get_location_service),
):
    return await service.add_favorite(location_id, user_id)


@router.delete("/{location_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_location(
    location_id: int,
    user_id: int = Depends(get_current_user_id),
    service: LocationService = Depends(get_location_service),
):
    await service.remove_favorite(location_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
