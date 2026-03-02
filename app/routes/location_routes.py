from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.locations_schemas import LocationCreate, LocationResponse
from app.crud import location_crud
from app.db.database import (
    get_async_session,
)

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/search", response_model=list[LocationResponse])
async def search_locations(
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    season_month: int | None = None,
    has_airport: bool | None = None,
    has_railway_station: bool | None = None,
    has_bus_station: bool | None = None,
    db: AsyncSession = Depends(get_async_session),
):
    locations = await location_crud.search_locations(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        season_month=season_month,
        has_airport=has_airport,
        has_railway_station=has_railway_station,
        has_bus_station=has_bus_station,
    )

    return [loc for loc in locations]


@router.get("/", response_model=list[LocationResponse])
async def read_locations(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)
):
    locations = await location_crud.get_locations(db=db, skip=skip, limit=limit)
    return [loc for loc in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def read_location(
    location_id: int, db: AsyncSession = Depends(get_async_session)
):
    location = await location_crud.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
