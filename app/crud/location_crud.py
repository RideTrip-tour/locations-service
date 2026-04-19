from __future__ import annotations

from datetime import datetime

from geoalchemy2.functions import ST_DWithin
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Activity,
    City,
    FavoriteLocation,
    Level,
    Location,
    LocationActivity,
    LocationLevel,
    Region,
    TripConfigLocation,
)
from app.schemas.locations_schemas import (
    LocationCreate,
    LocationSearchItem,
    SearchResponse,
    TripFilters,
)
from app.services.location_compatibility_service import LocationCompatibilityService


async def search_locations(
    db: AsyncSession,
    user_id: int | None = None,
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
    trip_filters: TripFilters | None = None,
) -> SearchResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    query = (
        select(Location)
        .options(selectinload(Location.region), selectinload(Location.city))
        .order_by(Location.id)
    )

    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(Location.name.ilike(pattern), Location.display_name.ilike(pattern), Location.description.ilike(pattern))
        )
    if region_id:
        conditions.append(Location.region_id == region_id)
    if city_id:
        conditions.append(Location.city_id == city_id)
    if season_month:
        conditions.append(and_(Location.season_start_month <= season_month, Location.season_end_month >= season_month))
    if has_airport is not None:
        conditions.append(Location.has_airport == has_airport)
    if has_railway_station is not None:
        conditions.append(Location.has_railway_station == has_railway_station)
    if has_bus_station is not None:
        conditions.append(Location.has_bus_station == has_bus_station)
    if latitude is not None and longitude is not None and radius_km is not None:
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        conditions.append(ST_DWithin(Location.coordinates, point, radius_km * 1000))
    if activity_id:
        query = query.join(LocationActivity, LocationActivity.location_id == Location.id)
        conditions.append(LocationActivity.activity_id == activity_id)
    if level_id:
        query = query.join(LocationLevel, LocationLevel.location_id == Location.id)
        conditions.append(LocationLevel.level_id == level_id)

    if conditions:
        query = query.where(and_(*conditions))

    total = (
        await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
    ).scalar_one()

    rows = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    favorite_ids: set[int] = set()
    if user_id:
        fav_rows = await db.execute(
            select(FavoriteLocation.location_id).where(FavoriteLocation.user_id == user_id)
        )
        favorite_ids = {rid for rid in fav_rows.scalars().all()}

    items = []
    for loc in rows:
        lat = lon = None
        if loc.coordinates is not None:
            point_wkt = (await db.execute(select(func.ST_AsText(loc.coordinates)))).scalar_one_or_none()
            if point_wkt and point_wkt.startswith("POINT(") and point_wkt.endswith(")"):
                lon_str, lat_str = point_wkt[6:-1].split(" ")
                lat = float(lat_str)
                lon = float(lon_str)

        status = "unknown"
        reason = None
        if trip_filters:
            status, reason = LocationCompatibilityService.check(loc, trip_filters)

        items.append(
            LocationSearchItem(
                id=loc.id,
                name=loc.name,
                display_name=loc.display_name,
                location_type=str(loc.location_type.value),
                region=loc.region.name if loc.region else None,
                city=loc.city.name if loc.city else None,
                latitude=lat,
                longitude=lon,
                description=loc.description,
                is_favorite=loc.id in favorite_ids,
                compatibility_status=status,
                compatibility_reason=reason,
            )
        )

    return SearchResponse(items=items, total=total, page=page, page_size=page_size, view=view)


async def get_location(db: AsyncSession, location_id: int) -> Location | None:
    result = await db.execute(select(Location).where(Location.id == location_id))
    return result.scalar_one_or_none()


async def get_locations(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Location]:
    result = await db.execute(select(Location).offset(skip).limit(limit))
    return list(result.scalars().all())


async def list_regions(db: AsyncSession) -> list[Region]:
    result = await db.execute(select(Region).order_by(Region.name))
    return list(result.scalars().all())


async def list_cities(db: AsyncSession, region_id: int | None = None) -> list[City]:
    query = select(City).order_by(City.name)
    if region_id is not None:
        query = query.where(City.region_id == region_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_activities(db: AsyncSession) -> list[Activity]:
    result = await db.execute(select(Activity).order_by(Activity.name))
    return list(result.scalars().all())


async def list_levels(db: AsyncSession) -> list[Level]:
    result = await db.execute(select(Level).order_by(Level.name))
    return list(result.scalars().all())


async def add_favorite(db: AsyncSession, user_id: int, location_id: int) -> None:
    existing = await db.execute(
        select(FavoriteLocation).where(
            FavoriteLocation.user_id == user_id, FavoriteLocation.location_id == location_id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(FavoriteLocation(user_id=user_id, location_id=location_id))
        await db.commit()


async def remove_favorite(db: AsyncSession, user_id: int, location_id: int) -> None:
    await db.execute(
        delete(FavoriteLocation).where(
            FavoriteLocation.user_id == user_id,
            FavoriteLocation.location_id == location_id,
        )
    )
    await db.commit()


async def list_favorites(db: AsyncSession, user_id: int) -> list[Location]:
    result = await db.execute(
        select(Location)
        .join(FavoriteLocation, FavoriteLocation.location_id == Location.id)
        .where(FavoriteLocation.user_id == user_id)
        .order_by(FavoriteLocation.created_at.desc())
    )
    return list(result.scalars().all())


async def save_trip_config_location(
    db: AsyncSession, user_id: int, config_id: int, location_id: int
) -> TripConfigLocation:
    current = await db.execute(
        select(TripConfigLocation).where(
            TripConfigLocation.user_id == user_id,
            TripConfigLocation.config_id == config_id,
        )
    )
    row = current.scalar_one_or_none()
    if row:
        row.location_id = location_id
        await db.commit()
        await db.refresh(row)
        return row

    row = TripConfigLocation(
        user_id=user_id,
        config_id=config_id,
        location_id=location_id,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def create_location(db: AsyncSession, location_in: LocationCreate) -> Location:
    payload = location_in.model_dump(exclude={"latitude", "longitude", "activity_ids", "level_ids"})
    location = Location(**payload)
    if location_in.latitude is not None and location_in.longitude is not None:
        location.coordinates = func.ST_SetSRID(func.ST_MakePoint(location_in.longitude, location_in.latitude), 4326)

    db.add(location)
    await db.flush()

    for activity_id in location_in.activity_ids:
        db.add(LocationActivity(location_id=location.id, activity_id=activity_id))
    for level_id in location_in.level_ids:
        db.add(LocationLevel(location_id=location.id, level_id=level_id))

    await db.commit()
    await db.refresh(location)
    return location
