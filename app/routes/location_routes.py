from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import location_crud
from app.db.database import get_async_session
from app.schemas.locations_schemas import (
    ActivityResponse,
    CompatibilityResponse,
    FavoriteActionResponse,
    HealthResponse,
    LevelResponse,
    LocationResponse,
    RegionResponse,
    CityResponse,
    SearchResponse,
    TripConfigSelectionRequest,
    TripConfigSelectionResponse,
    TripFilters,
)
from app.services.location_compatibility_service import LocationCompatibilityService

router = APIRouter(prefix="/locations", tags=["Locations"])


def _get_user_id(request: Request) -> int | None:
    value = request.state.user_id
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _require_user_id(request: Request) -> int:
    user_id = _get_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


@router.get("/health", response_model=HealthResponse)
async def locations_health() -> HealthResponse:
    return HealthResponse(status="ok", service="locations-service")


@router.get("/search", response_model=SearchResponse)
async def search_locations(
    request: Request,
    q: str | None = None,
    region_id: int | None = None,
    city_id: int | None = None,
    level_id: int | None = None,
    activity_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    season_month: int | None = None,
    has_airport: bool | None = None,
    has_railway_station: bool | None = None,
    has_bus_station: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    view: str = "list",
    db: AsyncSession = Depends(get_async_session),
):
    return await location_crud.search_locations(
        db=db,
        user_id=_get_user_id(request),
        q=q,
        region_id=region_id,
        city_id=city_id,
        level_id=level_id,
        activity_id=activity_id,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        season_month=season_month,
        has_airport=has_airport,
        has_railway_station=has_railway_station,
        has_bus_station=has_bus_station,
        page=page,
        page_size=page_size,
        view=view,
    )


@router.get("/map", response_model=SearchResponse)
async def map_locations(
    request: Request,
    region_id: int | None = None,
    city_id: int | None = None,
    activity_id: int | None = None,
    db: AsyncSession = Depends(get_async_session),
):
    return await location_crud.search_locations(
        db=db,
        user_id=_get_user_id(request),
        region_id=region_id,
        city_id=city_id,
        activity_id=activity_id,
        view="map",
        page_size=500,
    )


@router.get("/regions", response_model=list[RegionResponse])
async def list_regions(db: AsyncSession = Depends(get_async_session)):
    return await location_crud.list_regions(db)


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    region_id: int | None = None, db: AsyncSession = Depends(get_async_session)
):
    return await location_crud.list_cities(db, region_id)


@router.get("/activities", response_model=list[ActivityResponse])
async def list_activities(db: AsyncSession = Depends(get_async_session)):
    return await location_crud.list_activities(db)


@router.get("/levels", response_model=list[LevelResponse])
async def list_levels(db: AsyncSession = Depends(get_async_session)):
    return await location_crud.list_levels(db)


@router.post("/{location_id}/favorite", response_model=FavoriteActionResponse)
async def add_favorite(
    location_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    user_id = _require_user_id(request)
    await location_crud.add_favorite(db, user_id=user_id, location_id=location_id)
    return FavoriteActionResponse(location_id=location_id, is_favorite=True)


@router.delete("/{location_id}/favorite", response_model=FavoriteActionResponse)
async def remove_favorite(
    location_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    user_id = _require_user_id(request)
    await location_crud.remove_favorite(db, user_id=user_id, location_id=location_id)
    return FavoriteActionResponse(location_id=location_id, is_favorite=False)


@router.get("/favorites", response_model=list[LocationResponse])
async def favorites(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    user_id = _require_user_id(request)
    return await location_crud.list_favorites(db, user_id=user_id)


@router.post("/{location_id}/compatibility-check", response_model=CompatibilityResponse)
async def compatibility_check(
    location_id: int,
    trip_filters: TripFilters,
    db: AsyncSession = Depends(get_async_session),
):
    location = await location_crud.get_location(db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    status, reason = LocationCompatibilityService.check(location, trip_filters)
    return CompatibilityResponse(location_id=location_id, status=status, reason=reason)


@router.post("/trip-configs/{config_id}/location", response_model=TripConfigSelectionResponse)
async def save_location_to_trip_config(
    config_id: int,
    payload: TripConfigSelectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    user_id = _require_user_id(request)
    row = await location_crud.save_trip_config_location(
        db,
        user_id=user_id,
        config_id=config_id,
        location_id=payload.location_id,
    )
    return TripConfigSelectionResponse(
        config_id=config_id,
        location_id=row.location_id,
        saved_at=row.created_at,
    )


@router.get("/", response_model=list[LocationResponse])
async def read_locations(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)
):
    return await location_crud.get_locations(db=db, skip=skip, limit=limit)


@router.get("/{location_id}", response_model=LocationResponse)
async def read_location(location_id: int, db: AsyncSession = Depends(get_async_session)):
    location = await location_crud.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
