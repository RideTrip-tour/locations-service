from __future__ import annotations

import enum
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LocationKind(str, enum.Enum):
    resort = "resort"
    city = "city"
    hotel = "hotel"
    landmark = "landmark"


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    region: Mapped[Region] = relationship()

    __table_args__ = (UniqueConstraint("region_id", "name", name="uq_city_region_name"),)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)


class LocationActivity(Base):
    __tablename__ = "location_activities"

    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), primary_key=True)


class LocationLevel(Base):
    __tablename__ = "location_levels"

    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), primary_key=True)


class Location(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    location_type: Mapped[LocationKind] = mapped_column(
        Enum(LocationKind, name="location_kind"),
        nullable=False,
        default=LocationKind.resort,
    )

    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), index=True)

    coordinates = mapped_column(Geography(geometry_type="POINT", srid=4326))
    timezone: Mapped[str | None] = mapped_column(String(50))

    has_overnight_stay: Mapped[bool] = mapped_column(Boolean, default=False)
    has_food_service: Mapped[bool] = mapped_column(Boolean, default=False)
    has_airport: Mapped[bool] = mapped_column(Boolean, default=False)
    has_railway_station: Mapped[bool] = mapped_column(Boolean, default=False)
    has_bus_station: Mapped[bool] = mapped_column(Boolean, default=False)

    season_start_month: Mapped[int | None] = mapped_column(Integer)
    season_end_month: Mapped[int | None] = mapped_column(Integer)

    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    region: Mapped[Region | None] = relationship()
    city: Mapped[City | None] = relationship()
    activities: Mapped[list[Activity]] = relationship(secondary="location_activities")
    levels: Mapped[list[Level]] = relationship(secondary="location_levels")

    __table_args__ = (Index("ix_location_coordinates_gist", "coordinates", postgresql_using="gist"),)


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "location_id", name="uq_favorite_user_location"),)


class TripConfigLocation(Base):
    __tablename__ = "trip_config_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("config_id", "user_id", name="uq_trip_config_per_user"),)
