from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FavoriteLocation, Location


def _apply_text_filter(statement: Select, field, value: str):
    return statement.where(func.lower(field) == value.lower())


def _apply_array_filter(statement: Select, field, value: int | str):
    return statement.where(field.contains([value]))


def apply_location_filters(
    statement: Select,
    *,
    search: str | None = None,
    region: str | None = None,
    city: str | None = None,
    country: str | None = None,
    activity_id: int | None = None,
    style: str | None = None,
    level: str | None = None,
    is_active: bool | None = None,
):
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
        statement = _apply_array_filter(statement, Location.activity_ids, activity_id)
    if style:
        statement = _apply_array_filter(statement, Location.styles, style)
    if level:
        statement = _apply_array_filter(statement, Location.levels, level)
    if is_active is not None:
        statement = statement.where(Location.is_active.is_(is_active))

    return statement


async def get_location_by_id(session: AsyncSession, location_id: int) -> Location | None:
    result = await session.execute(select(Location).where(Location.id == location_id))
    return result.scalar_one_or_none()


async def get_location_by_slug(session: AsyncSession, slug: str) -> Location | None:
    result = await session.execute(select(Location).where(Location.slug == slug))
    return result.scalar_one_or_none()


async def list_locations(
    session: AsyncSession,
    *,
    search: str | None = None,
    region: str | None = None,
    city: str | None = None,
    country: str | None = None,
    activity_id: int | None = None,
    style: str | None = None,
    level: str | None = None,
    is_active: bool | None = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Location], int]:
    base_statement = apply_location_filters(
        select(Location),
        search=search,
        region=region,
        city=city,
        country=country,
        activity_id=activity_id,
        style=style,
        level=level,
        is_active=is_active,
    )

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
    region: str | None = None,
    city: str | None = None,
    country: str | None = None,
    activity_id: int | None = None,
    style: str | None = None,
    level: str | None = None,
    is_active: bool | None = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Location], int]:
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
        style=style,
        level=level,
        is_active=is_active,
    )

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
    statement = select(FavoriteLocation.location_id).where(FavoriteLocation.user_id == user_id)
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


async def list_location_filter_options(session: AsyncSession) -> dict[str, list[int] | list[str]]:
    filters = Location.is_active.is_(True)

    regions_result = await session.execute(
        select(Location.region).where(filters).distinct().order_by(Location.region)
    )
    cities_result = await session.execute(
        select(Location.city).where(filters, Location.city.is_not(None)).distinct().order_by(Location.city)
    )
    countries_result = await session.execute(
        select(Location.country).where(filters).distinct().order_by(Location.country)
    )
    activity_ids_result = await session.execute(
        select(func.unnest(Location.activity_ids)).where(filters).distinct()
    )
    styles_result = await session.execute(
        select(func.unnest(Location.styles)).where(filters).distinct()
    )
    levels_result = await session.execute(
        select(func.unnest(Location.levels)).where(filters).distinct()
    )

    return {
        "regions": [value for value in regions_result.scalars().all() if value is not None],
        "cities": [value for value in cities_result.scalars().all() if value is not None],
        "countries": [value for value in countries_result.scalars().all() if value is not None],
        "activity_ids": [int(value) for value in activity_ids_result.scalars().all() if value is not None],
        "styles": [value for value in styles_result.scalars().all() if value is not None],
        "levels": [value for value in levels_result.scalars().all() if value is not None],
    }
