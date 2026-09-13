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
)

ModelT = TypeVar("ModelT", Style, Level, City, Region, Country)
JunctionT = TypeVar("JunctionT", LocationLevel, LocationStyle, LocationActivity)
