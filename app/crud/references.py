from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.locations import _load_location_options
from app.db.models import Location
from app.types import JunctionT, ModelT


async def get_reference_by_id(
    session: AsyncSession, model: type[ModelT], item_id: int
) -> ModelT | None:
    result = await session.execute(select(model).where(model.id == item_id))
    return result.scalar_one_or_none()


async def list_references(
    session: AsyncSession,
    model: type[ModelT],
    *,
    name: str | None = None,
    id: int | list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[ModelT], int]:
    """Return a paginated list of reference rows filtered by optional name and id, ordered by name."""
    statement = select(model)
    if id is not None:
        if isinstance(id, list):
            if id:
                statement = statement.where(model.id.in_(id))
        else:
            statement = statement.where(model.id == id)
    if name:
        statement = statement.where(model.name.ilike(f"%{name.strip()}%"))

    total_statement = select(func.count()).select_from(statement.subquery())
    total = await session.scalar(total_statement)

    statement = statement.order_by(model.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all(), int(total or 0)


async def admin_create_reference(
    session: AsyncSession,
    model: type[ModelT],
    **fields,
) -> ModelT:
    item = model(**fields)
    session.add(item)
    await session.commit()
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
    await session.commit()
    return True


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
