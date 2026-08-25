from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

_DELETE_ORPHAN_CASCADE = "all, delete-orphan"
_LOCATION_ID_FOREIGN_KEY = "locations.id"


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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    favorites: Mapped[list[FavoriteLocation]] = relationship(
        back_populates="location", cascade=_DELETE_ORPHAN_CASCADE
    )
    activity_links: Mapped[list[LocationActivity]] = relationship(
        back_populates="location",
        cascade=_DELETE_ORPHAN_CASCADE,
        lazy="selectin",
        order_by="LocationActivity.position",
        passive_deletes=True,
    )
    style_links: Mapped[list[LocationStyle]] = relationship(
        back_populates="location",
        cascade=_DELETE_ORPHAN_CASCADE,
        lazy="selectin",
        order_by="LocationStyle.position",
        passive_deletes=True,
    )
    level_links: Mapped[list[LocationLevel]] = relationship(
        back_populates="location",
        cascade=_DELETE_ORPHAN_CASCADE,
        lazy="selectin",
        order_by="LocationLevel.position",
        passive_deletes=True,
    )

    @property
    def activity_ids(self) -> list[int]:
        return [link.activity_id for link in self.activity_links]

    @property
    def styles(self) -> list[str]:
        return [link.style_name for link in self.style_links]

    @property
    def levels(self) -> list[str]:
        return [link.level_name for link in self.level_links]

    __table_args__ = (
        Index("ix_locations_country_region_city", "country", "region", "city"),
        Index("ix_locations_region_lower", func.lower(region)),
        Index("ix_locations_city_lower", func.lower(city)),
        Index("ix_locations_country_lower", func.lower(country)),
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)

    location_links: Mapped[list[LocationActivity]] = relationship(
        back_populates="activity", passive_deletes=True
    )


class Style(Base):
    __tablename__ = "styles"

    name: Mapped[str] = mapped_column(String, primary_key=True)

    location_links: Mapped[list[LocationStyle]] = relationship(
        back_populates="style", passive_deletes=True
    )


class Level(Base):
    __tablename__ = "levels"

    name: Mapped[str] = mapped_column(String, primary_key=True)

    location_links: Mapped[list[LocationLevel]] = relationship(
        back_populates="level", passive_deletes=True
    )


class LocationActivity(Base):
    __tablename__ = "location_activities"

    location_id: Mapped[int] = mapped_column(
        ForeignKey(_LOCATION_ID_FOREIGN_KEY, ondelete="CASCADE"), primary_key=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    location: Mapped[Location] = relationship(back_populates="activity_links")
    activity: Mapped[Activity] = relationship(back_populates="location_links")

    __table_args__ = (
        UniqueConstraint(
            "location_id", "position", name="uq_location_activities_position"
        ),
        Index("ix_location_activities_activity_id", "activity_id"),
    )


class LocationStyle(Base):
    __tablename__ = "location_styles"

    location_id: Mapped[int] = mapped_column(
        ForeignKey(_LOCATION_ID_FOREIGN_KEY, ondelete="CASCADE"), primary_key=True
    )
    style_name: Mapped[str] = mapped_column(
        ForeignKey("styles.name", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    location: Mapped[Location] = relationship(back_populates="style_links")
    style: Mapped[Style] = relationship(back_populates="location_links")

    __table_args__ = (
        UniqueConstraint("location_id", "position", name="uq_location_styles_position"),
        Index("ix_location_styles_style_name", "style_name"),
    )


class LocationLevel(Base):
    __tablename__ = "location_levels"

    location_id: Mapped[int] = mapped_column(
        ForeignKey(_LOCATION_ID_FOREIGN_KEY, ondelete="CASCADE"), primary_key=True
    )
    level_name: Mapped[str] = mapped_column(
        ForeignKey("levels.name", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    location: Mapped[Location] = relationship(back_populates="level_links")
    level: Mapped[Level] = relationship(back_populates="location_links")

    __table_args__ = (
        UniqueConstraint("location_id", "position", name="uq_location_levels_position"),
        Index("ix_location_levels_level_name", "level_name"),
    )


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey(_LOCATION_ID_FOREIGN_KEY, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    location: Mapped[Location] = relationship(back_populates="favorites")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "location_id", name="uq_favorite_locations_user_location"
        ),
    )
