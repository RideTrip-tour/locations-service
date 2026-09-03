from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Level,
    Location,
    LocationActivity,
    LocationLevel,
    LocationStyle,
    Style,
)
from app.schemas.admin import AdminLocationCreate, AdminLocationRead
from app.types import JunctionT

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
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Location.name.ilike(pattern),
                Location.slug.ilike(pattern),
                Location.region.ilike(pattern),
                Location.city.ilike(pattern),
                Location.description.ilike(pattern),
            )
        )

    if region:
        statement = _apply_text_filter(statement, Location.region, region)
    if city:
        statement = _apply_text_filter(statement, Location.city, city)
    if country:
        statement = _apply_text_filter(statement, Location.country, country)
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
        .options(
            selectinload(Location.activities_rel),
            selectinload(Location.styles_rel).selectinload(LocationStyle.style),
            selectinload(Location.levels_rel).selectinload(LocationLevel.level),
        )
        .where(Location.id == location_id)
    )
    if only_active:
        statement = statement.where(Location.is_active.is_(True))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_location_by_slug(session: AsyncSession, slug: str) -> Location | None:
    result = await session.execute(
        select(Location)
        .options(
            selectinload(Location.activities_rel),
            selectinload(Location.styles_rel).selectinload(LocationStyle.style),
            selectinload(Location.levels_rel).selectinload(LocationLevel.level),
        )
        .where(Location.slug == slug)
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
        select(Location).options(
            selectinload(Location.activities_rel),
            selectinload(Location.styles_rel).selectinload(LocationStyle.style),
            selectinload(Location.levels_rel).selectinload(LocationLevel.level),
        ),
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        styles=styles,
        levels=levels,
        is_active=is_active,
    )

    total_statement = select(func.count()).select_from(base_statement.subquery())
    total = await session.scalar(total_statement)

    statement = base_statement.order_by(Location.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all(), int(total or 0)


async def list_location_filter_options(
    session: AsyncSession,
) -> dict[str, list[int] | list[str]]:
    filters = Location.is_active.is_(True)

    regions_result = await session.execute(
        select(Location.region).where(filters).distinct().order_by(Location.region)
    )
    cities_result = await session.execute(
        select(Location.city)
        .where(filters, Location.city.is_not(None))
        .distinct()
        .order_by(Location.city)
    )
    countries_result = await session.execute(
        select(Location.country).where(filters).distinct().order_by(Location.country)
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


async def admin_create_location(
    session: AsyncSession, locations_in: AdminLocationCreate
) -> AdminLocationRead:
    location_data = locations_in.model_dump(exclude_unset=True)
    activity_ids = location_data.pop("activity_ids", [])
    styles = location_data.pop("styles", [])
    levels = location_data.pop("levels", [])

    new_location = Location(**location_data)
    new_location.activities_rel = [
        LocationActivity(activity_id=activity_id) for activity_id in activity_ids
    ]
    style_rows = await session.execute(select(Style).where(Style.name.in_(styles)))
    style_rows = style_rows.scalars().all()
    new_location.styles_rel = [LocationStyle(style_id=style.id) for style in style_rows]
    level_rows = await session.execute(select(Level).where(Level.name.in_(levels)))
    level_rows = level_rows.scalars().all()
    new_location.levels_rel = [LocationLevel(level_id=level.id) for level in level_rows]
    session.add(new_location)

    await session.commit()
    await session.refresh(
        new_location,
        attribute_names=["activities_rel", "styles_rel", "levels_rel"],
    )

    return new_location


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
