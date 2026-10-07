from __future__ import annotations

from geoalchemy2.functions import ST_DWithin
from geoalchemy2 import WKBElement
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import Result, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import City, Location, LocationLevel, LocationStyle, Region
from app.types import CoordT, ModelT
from app.utils.geo import make_coords


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
    statement: Select,
    coords_column: InstrumentedAttribute[WKBElement],
    latitude: float,
    longitude: float,
    radius: float,
) -> Select:
    user_coords = make_coords(latitude, longitude)
    return statement.where(ST_DWithin(coords_column, user_coords, (radius * 1000)))


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
