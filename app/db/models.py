from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text, \
    Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


location_activities = Table(
    "location_activities",
    Base.metadata,
    Column(
        "location_id",
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "activity_id",
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True
    ),
)

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)

    locations: Mapped[list[Location]] = relationship(
        "Location",
        secondary=location_activities,
        back_populates="activities",
        lazy = "selectin",
    )


location_styles = Table(
    "location_styles",
    Base.metadata,
    Column(
        "location_id",
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "style_id",
        Integer,
        ForeignKey("styles.id", ondelete="CASCADE"),
        primary_key=True
    ),
)

class Style(Base):
    __tablename__ = "styles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)

    locations: Mapped[list[Location]] = relationship(
        "Location",
        secondary=location_styles,
        back_populates="styles",
        lazy = "selectin",
    )


location_levels = Table(
    "location_levels",
    Base.metadata,
    Column(
        "location_id",
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "level_id",
        Integer,
        ForeignKey("levels.id", ondelete="CASCADE"),
        primary_key=True
    ),
)

class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)

    locations: Mapped[list[Location]] = relationship(
        "Location",
        secondary=location_levels,
        back_populates="levels"
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    region: Mapped[str] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    country: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        server_default=text("'Russia'"),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_to_city_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activities: Mapped[list[Activity]] = relationship(
        secondary=location_activities,
        back_populates="locations"
    )
    @property
    def activity_ids(self) -> list[int]:
        return [a.id for a in self.activities] if self.activities else []

    styles: Mapped[list[Style]] = relationship(
        secondary=location_styles,
        back_populates="locations"
    )
    levels: Mapped[list[Level]] = relationship(
        secondary=location_levels,
        back_populates="locations"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    favorites: Mapped[list["FavoriteLocation"]] = relationship(back_populates="location", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_locations_country_region_city", "country", "region", "city"),
        Index("ix_locations_region_lower", func.lower(region)),
        Index("ix_locations_city_lower", func.lower(city)),
        Index("ix_locations_country_lower", func.lower(country))
    )


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location: Mapped[Location] = relationship(back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "location_id", name="uq_favorite_locations_user_location"),)



