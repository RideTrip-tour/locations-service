from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import Result, Select, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.locations import _load_location_options
from app.db.models import City, Location, Region
from app.types import JunctionT, ModelT


async def get_reference_by_id(
    session: AsyncSession, model: type[ModelT], item_id: int
) -> ModelT | None:
    result = await session.execute(select(model).where(model.id == item_id))
    return result.scalar_one_or_none()


async def _paginate_and_search_reference(
    session: AsyncSession,
    model: type[ModelT],
    statement: Select,
    *,
    name: str | None = None,
    item_id: int | list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Result, int]:
    """Pagination and filter by optional name and id, ordered by name for references."""
    if item_id is not None:
        if isinstance(item_id, list):
            if item_id:
                statement = statement.where(model.id.in_(item_id))
        else:
            statement = statement.where(model.id == item_id)
    if name:
        statement = statement.where(model.name.ilike(f"%{name.strip()}%"))

    total_statement = select(func.count()).select_from(statement.subquery())
    total = await session.scalar(total_statement)

    statement = statement.order_by(model.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result, int(total or 0)


async def list_references(
    session: AsyncSession,
    model: type[ModelT],
    *,
    name: str | None = None,
    id: int | list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[ModelT], int]:
    """Return a paginated list of reference rows."""
    statement = select(model)
    result, total = await _paginate_and_search_reference(
        session=session,
        model=model,
        statement=statement,
        name=name,
        item_id=id,
        limit=limit,
        offset=offset,
    )
    return result.scalars().all(), int(total or 0)


async def list_cities_with_coords(
    session: AsyncSession,
    *,
    name: str | None = None,
    id: int | list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list, int]:
    """Return a paginated list of cities with coordinates for admin."""
    statement = select(
        City.id,
        City.name,
        ST_Y(cast(City.coords, Geometry)).label("latitude"),
        ST_X(cast(City.coords, Geometry)).label("longitude"),
    )

    result, total = await _paginate_and_search_reference(
        session=session,
        model=City,
        statement=statement,
        name=name,
        item_id=id,
        limit=limit,
        offset=offset,
    )

    return [row._mapping for row in result], int(total or 0)


async def admin_create_reference(
    session: AsyncSession,
    model: type[ModelT],
    **fields,
) -> ModelT:
    item = model(**fields)
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(item)
    return item


async def admin_update_reference(
    session: AsyncSession,
    model: type[ModelT],
    item_id: int,
    **fields,
) -> ModelT | None:
    item = await get_reference_by_id(session, model, item_id)
    if item is None:
        return None
    for field, value in fields.items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return item


async def admin_delete_reference(
    session: AsyncSession,
    model: type[ModelT],
    item_id: int,
) -> bool:
    item = await get_reference_by_id(session, model, item_id)
    if item is None:
        return False

    await session.delete(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return True


async def get_city_names_by_region(
    session: AsyncSession, region_id: int
) -> Sequence[str]:
    """Return names of all cities belonging to a region."""
    statement = select(City.name).where(City.region_id == region_id)
    result = await session.execute(statement)
    return result.scalars().all()


async def get_city_names_by_country(
    session: AsyncSession, country_id: int
) -> Sequence[str]:
    """Return names of all cities belonging to a country (through its regions)."""
    statement = (
        select(City.name)
        .join(Region, City.region_id == Region.id)
        .where(Region.country_id == country_id)
    )
    result = await session.execute(statement)
    return result.scalars().all()


async def list_locations_by_reference(
    session: AsyncSession,
    item_id: int,
    junction_model: type[JunctionT],
    reference_field: Any,
    *,
    is_active: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Location], int]:
    """Return a paginated list of locations linked to a reference row.

    Filter by is_active when provided; otherwise returns both active and inactive.
    """

    base_statement = (
        select(Location)
        .options(*_load_location_options())
        .join(junction_model, junction_model.location_id == Location.id)
        .where(reference_field == item_id)
    )
    if is_active is not None:
        base_statement = base_statement.where(Location.is_active.is_(is_active))

    total_statement = select(func.count()).select_from(base_statement.subquery())
    total = await session.scalar(total_statement)

    statement = base_statement.order_by(Location.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all(), int(total or 0)
