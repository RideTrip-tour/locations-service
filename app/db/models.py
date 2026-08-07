from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


style_location_association = Table(
    "style_location_association",
    Base.metadata,
    Column("style", String(255), ForeignKey("styles.name", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),

    Index("ix_style_location_style", "style"),
    Index("ix_style_location_location_id", "location_id"),
)


class Style(Base):
    __tablename__ = "styles"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    locations: Mapped[list["Location"]] = relationship(
        "Location",
        secondary=style_location_association,
        back_populates="styles",
        lazy="selectin"
    )


level_location_association = Table(
    "level_location_association",
    Base.metadata,
    Column("level_id", Integer, ForeignKey("levels.name", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),

    Index("ix_level_location_level_id", "level_id"),
    Index("ix_level_location_location_id", "location_id"),
)


class Level(Base):
    __tablename__ = "levels"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)

    locations: Mapped[list["Location"]] = relationship(
        "Location",
        secondary=level_location_association,
        back_populates="levels",
        lazy="selectin"
    )


activity_location_association = Table(
    "activity_location_association",
    Base.metadata,
    Column("activity_id", Integer, ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),

    Index("ix_activity_location_activity_id", "activity_id"),
    Index("ix_activity_location_location_id", "location_id"),
)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    locations: Mapped[list["Location"]] = relationship(
        "Location",
        secondary=activity_location_association,
        back_populates="activity_ids",
        lazy="selectin"
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
    activity_ids: Mapped[list["Activity"]] = relationship(
            "Activity",
            secondary=activity_location_association,
            back_populates="locations",
            lazy="selectin"
        )
    styles: Mapped[list["Style"]] = relationship(
        "Style",
        secondary=style_location_association,
        back_populates="locations",
        lazy="selectin"
    )
    levels: Mapped[list["Level"]] = relationship(
        "Level",
        secondary=level_location_association,
        back_populates="locations",
        lazy="selectin"
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
        Index("ix_locations_country_lower", func.lower(country)),
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
