from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.functions import ST_Distance
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.common import filter_within_radius, load_location_options, paginate
from app.db.models import (
    City,
    Country,
    Level,
    Location,
    LocationActivity,
    LocationLevel,
    LocationStyle,
    Region,
    Style,
)
from app.exceptions import CityNotFoundError
from app.schemas.admin import AdminLocationCreate, AdminLocationUpdate
from app.types import JunctionT
from app.utils.geo import make_coords

StrFilter = str | Sequence[str]
IntFilter = int | Sequence[int]


def _as_sequence[T](value: T | Sequence[T] | None) -> list[T]:
    """Convert a scalar or sequence filter value to a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _normalize_text_values(value: StrFilter | None) -> list[str]:
    """Lowercase and split text filter values from scalar, list, or CSV input."""
    values: list[str] = []
    for item in _as_sequence(value):
        values.extend(part.strip().lower() for part in item.split(",") if part.strip())
    return values


def _normalize_int_values(value: IntFilter | None) -> list[int]:
    """Split and cast integer filter values from scalar, list, or CSV input."""
    values: list[int] = []
    for item in _as_sequence(value):
        if isinstance(item, str):
            values.extend(int(part.strip()) for part in item.split(",") if part.strip())
        else:
            values.append(item)
    return values


def _apply_filter_via_junction_table(
    statement: Select,
    values: list[str] | list[int],
    model: type[JunctionT],
    model_field: Any,
    join_model: Any | None = None,
    join_on: Any | None = None,
    *,
    is_lower: bool = False,
):
    """Apply filter via junction table, optionally joined to a name table."""
    if not values:
        return statement
    filter_field = func.lower(model_field) if is_lower else model_field
    query = select(1).select_from(model)
    if join_model is not None and join_on is not None:
        query = query.where(join_on)
    return statement.where(
        query.where(
            and_(
                model.location_id == Location.id,
                filter_field.in_(values),
            )
        ).exists()
    )


def _apply_text_filter(statement: Select, field, value: StrFilter | None):
    """Apply a case-insensitive IN filter for a single text column."""
    values = _normalize_text_values(value)
    if not values:
        return statement
    return statement.where(func.lower(field).in_(values))


def _apply_activity_filter(
    statement: Select,
    value: IntFilter | None,
):
    """Apply filter via location_activities junction table."""
    return _apply_filter_via_junction_table(
        statement=statement,
        values=_normalize_int_values(value),
        model=LocationActivity,
        model_field=LocationActivity.activity_id,
    )


def _apply_style_filter(
    statement: Select,
    value: StrFilter | None,
):
    """Apply filter via location_styles joined to styles."""
    return _apply_filter_via_junction_table(
        statement=statement,
        values=_normalize_text_values(value),
        model=LocationStyle,
        model_field=Style.name,
        join_model=Style,
        join_on=Style.id == LocationStyle.style_id,
        is_lower=True,
    )


def _apply_level_filter(
    statement: Select,
    value: StrFilter | None,
):
    """Apply filter via location_levels joined to levels."""
    return _apply_filter_via_junction_table(
        statement=statement,
        values=_normalize_text_values(value),
        model=LocationLevel,
        model_field=Level.name,
        join_model=Level,
        join_on=Level.id == LocationLevel.level_id,
        is_lower=True,
    )


def _add_geo_joins(
    statement: Select,
    *,
    search: str | None = None,
    region: StrFilter | None = None,
    city: StrFilter | None = None,
    country: StrFilter | None = None,
):
    """Join city - region - country chain."""
    if search or region or city or country:
        statement = (
            statement.join(City, City.id == Location.city_id)
            .join(Region, Region.id == City.region_id)
            .join(Country, Country.id == Region.country_id)
        )
    return statement


async def _get_distance_to_city_km(
    session: AsyncSession,
    *,
    location_coords: WKBElement,
    city_id: int,
) -> Decimal | None:
    result = await session.execute(
        select(
            ST_Distance(
                location_coords,
                City.coords,
            )
        ).where(City.id == city_id)
    )
    distance_m = result.scalars().first()
    if distance_m is None:
        return None
    return (Decimal(str(distance_m)) / Decimal(1000)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )


async def _get_existing_style_names(session: AsyncSession) -> set[str]:
    result = await session.execute(select(Style.name))
    return set(result.scalars().all())


async def _get_existing_level_names(session: AsyncSession) -> set[str]:
    result = await session.execute(select(Level.name))
    return set(result.scalars().all())


async def get_reference_options(session: AsyncSession) -> dict[str, set]:
    """activity_ids пока не проверяется."""
    return {
        "styles": await _get_existing_style_names(session),
        "levels": await _get_existing_level_names(session),
    }


def apply_location_filters(
    statement: Select,
    *,
    search: str | None = None,
    region: StrFilter | None = None,
    city: StrFilter | None = None,
    country: StrFilter | None = None,
    activity_id: IntFilter | None = None,
    styles: StrFilter | None = None,
    levels: StrFilter | None = None,
    is_active: bool | None = None,
):
    """Apply search and location filters, using OR inside fields and AND between fields."""
    statement = _add_geo_joins(
        statement=statement, search=search, region=region, city=city, country=country
    )
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Location.name.ilike(pattern),
                Location.slug.ilike(pattern),
                City.name.ilike(pattern),
                Region.name.ilike(pattern),
                Country.name.ilike(pattern),
                Location.description.ilike(pattern),
            )
        )
    if region:
        statement = _apply_text_filter(statement, Region.name, region)
    if city:
        statement = _apply_text_filter(statement, City.name, city)
    if country:
        statement = _apply_text_filter(statement, Country.name, country)
    if activity_id:
        statement = _apply_activity_filter(statement, activity_id)
    if styles:
        statement = _apply_style_filter(statement, styles)
    if levels:
        statement = _apply_level_filter(statement, levels)
    if is_active is not None:
        statement = statement.where(Location.is_active.is_(is_active))

    return statement


async def get_location_by_id(
    session: AsyncSession,
    location_id: int,
    *,
    only_active: bool = True,
) -> Location | None:
    statement = (
        select(Location)
        .options(*load_location_options())
        .where(Location.id == location_id)
    )
    if only_active:
        statement = statement.where(Location.is_active.is_(True))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_location_by_slug(session: AsyncSession, slug: str) -> Location | None:
    result = await session.execute(
        select(Location).options(*load_location_options()).where(Location.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_locations(
    session: AsyncSession,
    *,
    search: str | None = None,
    region: StrFilter | None = None,
    city: StrFilter | None = None,
    country: StrFilter | None = None,
    activity_id: IntFilter | None = None,
    styles: StrFilter | None = None,
    levels: StrFilter | None = None,
    is_active: bool | None = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Location], int]:
    """Return a paginated filtered location list and the total matching count."""
    base_statement = apply_location_filters(
        select(Location).options(*load_location_options()),
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        styles=styles,
        levels=levels,
        is_active=is_active,
    )

    result, total = await paginate(
        session=session,
        statement=base_statement,
        model=Location,
        limit=limit,
        offset=offset,
    )
    return result.scalars().all(), int(total or 0)


async def list_location_filter_options(
    session: AsyncSession,
) -> dict[str, list[int] | list[str]]:
    filters = Location.is_active.is_(True)

    regions_result = await session.execute(
        select(Region.name)
        .join(City, City.region_id == Region.id)
        .join(Location, Location.city_id == City.id)
        .where(filters)
        .distinct()
    )
    cities_result = await session.execute(
        select(City.name)
        .join(Location, Location.city_id == City.id)
        .where(filters)
        .distinct()
    )
    countries_result = await session.execute(
        select(Country.name)
        .join(Region, Region.country_id == Country.id)
        .join(City, City.region_id == Region.id)
        .join(Location, Location.city_id == City.id)
        .where(filters)
        .distinct()
    )
    activity_ids_result = await session.execute(
        select(LocationActivity.activity_id).distinct()
    )
    styles_result = await session.execute(
        select(Style.name)
        .join(LocationStyle, LocationStyle.style_id == Style.id)
        .distinct()
    )
    levels_result = await session.execute(
        select(Level.name)
        .join(LocationLevel, LocationLevel.level_id == Level.id)
        .distinct()
    )

    return {
        "regions": [
            value for value in regions_result.scalars().all() if value is not None
        ],
        "cities": [
            value for value in cities_result.scalars().all() if value is not None
        ],
        "countries": [
            value for value in countries_result.scalars().all() if value is not None
        ],
        "activity_ids": [
            int(value)
            for value in activity_ids_result.scalars().all()
            if value is not None
        ],
        "styles": [
            value for value in styles_result.scalars().all() if value is not None
        ],
        "levels": [
            value for value in levels_result.scalars().all() if value is not None
        ],
    }


async def list_locations_within_radius(
    session: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius: float,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Location], int]:
    statement = filter_within_radius(
        Location, latitude=latitude, longitude=longitude, radius=radius
    ).options(*load_location_options())

    result, total = await paginate(
        session=session, statement=statement, model=Location, limit=limit, offset=offset
    )
    return result.scalars().all(), int(total or 0)


async def _build_relations(
    session: AsyncSession,
    *,
    activity_ids: list[int] | None,
    styles: list[str] | None,
    levels: list[str] | None,
) -> tuple[list, list, list]:
    activities_rel = None
    styles_rel = None
    levels_rel = None

    if activity_ids is not None:
        activities_rel = [
            LocationActivity(activity_id=activity_id) for activity_id in activity_ids
        ]
    if styles is not None:
        style_result = await session.execute(
            select(Style).where(Style.name.in_(styles))
        )
        style_rows = style_result.scalars().all()
        styles_rel = [LocationStyle(style_id=style.id) for style in style_rows]
    if levels is not None:
        level_result = await session.execute(
            select(Level).where(Level.name.in_(levels))
        )
        level_rows = level_result.scalars().all()
        levels_rel = [LocationLevel(level_id=level.id) for level in level_rows]
    return activities_rel, styles_rel, levels_rel


async def _ensure_city_exists(session: AsyncSession, city_id: int) -> City:
    city = await session.execute(select(City).where(City.id == city_id))
    result = city.scalar_one_or_none()
    if result is None:
        raise CityNotFoundError(city_id)
    return result


async def admin_create_location(
    session: AsyncSession, locations_in: AdminLocationCreate, *, slug: str
) -> Location:
    location_data = locations_in.model_dump(exclude_unset=True)
    activity_ids = location_data.pop("activity_ids", [])
    styles = location_data.pop("styles", [])
    levels = location_data.pop("levels", [])

    location_data.pop("slug", None)

    city_id = location_data.pop("city_id")
    latitude = location_data.pop("latitude")
    longitude = location_data.pop("longitude")
    location_coords = make_coords(latitude, longitude)

    await _ensure_city_exists(session, city_id)

    new_location = Location(
        **location_data,
        city_id=city_id,
        slug=slug,
        coords=location_coords,
        distance_to_city_km=await _get_distance_to_city_km(
            session, location_coords=location_coords, city_id=city_id
        ),
    )
    activities_rel, styles_rel, levels_rel = await _build_relations(
        session, activity_ids=activity_ids, styles=styles, levels=levels
    )
    new_location.activities_rel = activities_rel or []
    new_location.styles_rel = styles_rel or []
    new_location.levels_rel = levels_rel or []

    session.add(new_location)
    await session.commit()

    result = await session.execute(
        select(Location)
        .options(*load_location_options())
        .where(Location.id == new_location.id)
    )
    return result.scalar_one()


async def admin_update_location(
    session: AsyncSession,
    location_id: int,
    location_in: AdminLocationUpdate,
) -> Location | None:
    location = await get_location_by_id(session, location_id, only_active=False)
    if location is None:
        return None

    fields = location_in.model_dump(exclude_unset=True)
    activity_ids = fields.pop("activity_ids", None)
    styles = fields.pop("styles", None)
    levels = fields.pop("levels", None)
    city_id = fields.pop("city_id", None)
    latitude = fields.pop("latitude", None)
    longitude = fields.pop("longitude", None)

    if city_id is not None:
        city = await _ensure_city_exists(session, city_id)
        location.city_id = city_id
        location.city_rel = city

    new_coords = latitude is not None and longitude is not None
    if new_coords:
        location.coords = make_coords(latitude, longitude)
    if city_id is not None or new_coords:
        distance = await _get_distance_to_city_km(
            session,
            location_coords=location.coords,
            city_id=location.city_id,
        )
        if distance is not None:
            location.distance_to_city_km = distance

    for field, value in fields.items():
        setattr(location, field, value)

    activities_rel, styles_rel, levels_rel = await _build_relations(
        session, activity_ids=activity_ids, styles=styles, levels=levels
    )
    if activity_ids is not None:
        location.activities_rel = activities_rel
    if styles is not None:
        location.styles_rel = styles_rel
    if levels is not None:
        location.levels_rel = levels_rel

    if not location_in.model_fields_set:
        return location

    await session.commit()
    result = await session.execute(
        select(Location)
        .options(*load_location_options())
        .where(Location.id == location_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def admin_delete_location_by_id(session: AsyncSession, location_id: int) -> bool:
    """
    Удаляет локацию по id.
    Возвращает True если удален, иначе False.
    """

    result = await session.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()

    if not location:
        return False

    await session.delete(location)
    await session.commit()

    return True
