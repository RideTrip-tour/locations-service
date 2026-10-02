from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_X, ST_Y, ST_DWithin
from sqlalchemy import Result, Select, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import City, Location, Region, LocationStyle, LocationLevel
from app.types import JunctionT, ModelT, CoordT
from app.utils.geo import make_coords
from sqlalchemy.orm import joinedload, selectinload


async def paginate(
    session: AsyncSession,
    statement: Select,
    model: type[ModelT],
    limit: int = 20,
    offset: int = 0,
) -> tuple[Result, int]:
    total_statement = select(func.count()).select_from(statement.subquery())
    total = await session.scalar(total_statement)

    statement = statement.order_by(model.name).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result, int(total or 0)


def filter_within_radius(
    model: type[CoordT],
    latitude: float,
    longitude: float,
    radius: float,
) -> Select:
    user_coords = make_coords(latitude, longitude)
    return select(model).where(
        ST_DWithin(model.coords, user_coords, (radius * 1000))
    )


def load_location_options():
    """Load relationships for location."""
    return (
        selectinload(Location.activities_rel),
        selectinload(Location.styles_rel).selectinload(LocationStyle.style),
        selectinload(Location.levels_rel).selectinload(LocationLevel.level),
        joinedload(Location.city_rel)
        .joinedload(City.region)
        .joinedload(Region.country),
    )
