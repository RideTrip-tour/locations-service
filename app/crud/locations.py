from __future__ import annotations
from fastapi import HTTPException
from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import Select, and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import AdminLocationCreate
from app.db.models import (
    Activity,
    FavoriteLocation,
    Location,
    Level,
    Style,
    LocationActivity,
    LocationLevel,
    LocationStyle
)

T = TypeVar("T", int, str)
StrFilter = str | Sequence[str]
IntFilter = int | Sequence[int]


def _as_sequence(value: T | Sequence[T] | None) -> list[T]:
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


def _apply_text_filter(statement: Select, field, value: StrFilter | None):
    """Apply a case-insensitive IN filter for a single text column."""
    values = _normalize_text_values(value)
    if not values:
        return statement
    return statement.where(func.lower(field).in_(values))


def _apply_relation_filter(
    statement: Select,
    between_model,
    foreign_key,
    related_model,
    values
):
    statement = statement.join(
        between_model, between_model.location_id == Location.id,
        ).join(
            related_model, related_model.id == foreign_key
            ).where(
                func.lower(related_model.name).in_(values))
    return statement


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
    if activity_id is not None:
        statement = statement.join(
            LocationActivity,
            LocationActivity.location_id == Location.id
        ).where(
            LocationActivity.activity_id.in_(
                _normalize_int_values(activity_id)
            )
        )
    if styles:
        statement = _apply_relation_filter(statement, LocationStyle, LocationStyle.style_id, Style, _normalize_text_values(styles))
    if levels:
        statement = _apply_relation_filter(statement, LocationLevel, LocationLevel.level_id, Level, _normalize_text_values(levels))
    if is_active is not None:
        statement = statement.where(Location.is_active.is_(is_active))

    return statement


async def get_location_by_id(
    session: AsyncSession,
    location_id: int,
    *,
    only_active: bool = True,
) -> Location | None:
    statement = select(Location).where(Location.id == location_id)
    if only_active:
        statement = statement.where(Location.is_active.is_(True))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_location_by_slug(session: AsyncSession, slug: str) -> Location | None:
    result = await session.execute(select(Location).where(Location.slug == slug))
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
        select(Location),
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        styles=styles,
        levels=levels,
        is_active=is_active,
    )
    base_statement = base_statement.distinct()

    total_statement = select(func.count()).select_from(base_statement.subquery())
    total = await session.scalar(total_statement)

    statement = base_statement.order_by(Location.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all(), int(total or 0)


async def list_favorite_locations(
    session: AsyncSession,
    *,
    user_id: int,
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
    """Return a paginated filtered list of a user's favorite locations and total count."""
    base_statement = (
        select(Location)
        .join(FavoriteLocation, FavoriteLocation.location_id == Location.id)
        .where(FavoriteLocation.user_id == user_id)
    )
    base_statement = apply_location_filters(
        base_statement,
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        styles=styles,
        levels=levels,
        is_active=is_active,
    )
    base_statement = base_statement.distinct()

    total_statement = select(func.count()).select_from(base_statement.subquery())
    total = await session.scalar(total_statement)

    statement = base_statement.order_by(Location.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all(), int(total or 0)


async def list_favorite_location_ids(
    session: AsyncSession,
    *,
    user_id: int,
    location_ids: list[int] | None = None,
) -> set[int]:
    statement = select(FavoriteLocation.location_id).where(
        FavoriteLocation.user_id == user_id
    )
    if location_ids:
        statement = statement.where(FavoriteLocation.location_id.in_(location_ids))
    result = await session.execute(statement)
    return {row[0] for row in result.all()}


async def add_favorite_location(
    session: AsyncSession,
    *,
    user_id: int,
    location_id: int,
) -> FavoriteLocation:
    favorite = FavoriteLocation(user_id=user_id, location_id=location_id)
    session.add(favorite)
    await session.flush()
    await session.refresh(favorite)
    return favorite


async def remove_favorite_location(
    session: AsyncSession,
    *,
    user_id: int,
    location_id: int,
) -> bool:
    result = await session.execute(
        delete(FavoriteLocation).where(
            and_(
                FavoriteLocation.user_id == user_id,
                FavoriteLocation.location_id == location_id,
            )
        )
    )
    return result.rowcount > 0


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
        select(LocationActivity.activity_id).join(
            Location, Location.id == LocationActivity.location_id
        ).where(filters).distinct()
    )
    styles_result = await session.execute(
        select(
            Style.name
        ).join(
            LocationStyle, LocationStyle.style_id == Style.id
        ).join(
            Location, Location.id == LocationStyle.location_id
        ).where(filters).distinct()
    )
    levels_result = await session.execute(
        select(
            Level.name
        ).join(
            LocationLevel, LocationLevel.level_id == Level.id
        ).join(
            Location, Location.id == LocationLevel.location_id
        ).where(filters).distinct()
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
) -> Location:
    location_data = locations_in.model_dump(exclude={
        "activity_ids",
        "styles",
        "levels",
    })
    new_location = Location(**location_data)
    session.add(new_location)
    await session.flush()

    found_activities = set(await session.scalars(select(Activity.id).where(Activity.id.in_(locations_in.activity_ids))))
    not_found_activities = set(locations_in.activity_ids) - found_activities
    if not_found_activities:
        raise HTTPException(status_code=400, detail=f"Activities not found: {sorted(not_found_activities)}")
    session.add_all(
        [LocationActivity(
            location_id=new_location.id,
            activity_id=activity) for activity in found_activities]
    )

    found_styles = list(await session.scalars(select(Style).where(Style.name.in_(locations_in.styles))))
    found_styles_names = set(style.name for style in found_styles)
    not_found_styles_names = set(locations_in.styles) - found_styles_names
    if not_found_styles_names:
        raise HTTPException(status_code=400, detail=f"Styles not found: {sorted(not_found_styles_names)}")     
    session.add_all(
        [LocationStyle(
            location_id=new_location.id,
            style_id=style.id) for style in found_styles]
    )

    found_levels = list(await session.scalars(select(Level).where(Level.name.in_(locations_in.levels))))
    found_level_names = set(level.name for level in found_levels)
    not_found_level_names = set(locations_in.levels) - found_level_names
    if not_found_level_names:
        raise HTTPException(status_code=400, detail=f"Styles not found: {sorted(not_found_level_names)}")     
    session.add_all(
        [LocationLevel(
            location_id=new_location.id,
            level_id=level.id) for level in found_levels]
    )

    await session.commit()
    await session.refresh(new_location)
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
