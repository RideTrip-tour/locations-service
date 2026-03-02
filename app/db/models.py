from sqlalchemy import String, Integer, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from geoalchemy2 import Geography
from app.db.base import Base
from typing import Optional
import enum
from datetime import datetime


class ActivityEnum(str, enum.Enum):
    hiking = "hiking"
    skiing = "skiing"
    swimming = "swimming"


class Location(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    coordinates: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326)
    )

    timezone: Mapped[Optional[str]] = mapped_column(String(50))

    has_overnight_stay: Mapped[bool] = mapped_column(Boolean, default=False)
    has_food_service: Mapped[bool] = mapped_column(Boolean, default=False)
    has_airport: Mapped[bool] = mapped_column(Boolean, default=False)
    has_railway_station: Mapped[bool] = mapped_column(Boolean, default=False)
    has_bus_station: Mapped[bool] = mapped_column(Boolean, default=False)

    available_activities: Mapped[Optional[ActivityEnum]] = mapped_column(
        Enum(ActivityEnum, name="activity_enum")
    )

    season_start_month: Mapped[Optional[int]] = mapped_column(Integer)
    season_end_month: Mapped[Optional[int]] = mapped_column(Integer)

    description: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Location {self.location_id}: {self.name}>"
