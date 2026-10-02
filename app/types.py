from __future__ import annotations

from typing import TypeVar

from app.db.models import (
    City,
    Country,
    Level,
    LocationActivity,
    LocationLevel,
    LocationStyle,
    Region,
    Style,
    Location
)

ModelT = TypeVar("ModelT", Style, Level, City, Region, Country, Location)
ParentModelT = TypeVar("ParentModelT", Region, Country)
JunctionT = TypeVar("JunctionT", LocationLevel, LocationStyle, LocationActivity)
CoordT = TypeVar("CoordT", City, Location)
