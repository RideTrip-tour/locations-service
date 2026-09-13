from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db.base import Base


class LocationChildMixin:
    """Shared columns and relationship for location junction tables."""

    _location_back_populates: str

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )

    @declared_attr
    def location(cls) -> Mapped[Location]:
        return relationship(back_populates=cls._location_back_populates)


class ReferenceMixin:
    """Shared columns for normalized tables with name."""

    _name_unique: bool = False

    id: Mapped[int] = mapped_column(primary_key=True)

    @declared_attr
    def name(cls) -> Mapped[str]:
        return mapped_column(String(150), unique=cls._name_unique)


class LocationActivity(LocationChildMixin, Base):
    __tablename__ = "location_activities"
    _location_back_populates = "activities_rel"

    activity_id: Mapped[int] = mapped_column(primary_key=True)


class Style(ReferenceMixin, Base):
    __tablename__ = "styles"
    _name_unique = True

    location_styles: Mapped[list[LocationStyle]] = relationship(back_populates="style")


class LocationStyle(LocationChildMixin, Base):
    __tablename__ = "location_styles"
    _location_back_populates = "styles_rel"

    style_id: Mapped[int] = mapped_column(
        ForeignKey("styles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    style: Mapped[Style] = relationship(back_populates="location_styles")


class Level(ReferenceMixin, Base):
    __tablename__ = "levels"
    _name_unique = True

    location_levels: Mapped[list[LocationLevel]] = relationship(back_populates="level")


class LocationLevel(LocationChildMixin, Base):
    __tablename__ = "location_levels"
    _location_back_populates = "levels_rel"

    level_id: Mapped[int] = mapped_column(
        ForeignKey("levels.id", ondelete="CASCADE"),
        primary_key=True,
    )

    level: Mapped[Level] = relationship(back_populates="location_levels")


class Country(ReferenceMixin, Base):
    __tablename__ = "countries"
    _name_unique = True

    regions: Mapped[list[Region]] = relationship(back_populates="country")


class Region(ReferenceMixin, Base):
    __tablename__ = "regions"

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True, nullable=False
    )

    country: Mapped[Country] = relationship(back_populates="regions")
    cities: Mapped[list[City]] = relationship(back_populates="region")

    __table_args__ = (
        UniqueConstraint("name", "country_id", name="uq_region_name_country"),
    )


class City(ReferenceMixin, Base):
    __tablename__ = "cities"

    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), index=True, nullable=False
    )

    region: Mapped[Region] = relationship(back_populates="cities")
    locations: Mapped[list[Location]] = relationship(
        back_populates="city_rel", foreign_keys="Location.city_id"
    )

    __table_args__ = (
        UniqueConstraint("name", "region_id", name="uq_city_name_region"),
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id"), nullable=False, index=True
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
    activities_rel: Mapped[list[LocationActivity]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    styles_rel: Mapped[list[LocationStyle]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    levels_rel: Mapped[list[LocationLevel]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    city_rel: Mapped[City] = relationship(
        back_populates="locations", foreign_keys="Location.city_id"
    )

    @property
    def activity_ids(self) -> list[int]:
        return [activity.activity_id for activity in self.activities_rel]

    @property
    def styles(self) -> list[str]:
        return [style.style.name for style in self.styles_rel]

    @property
    def levels(self) -> list[str]:
        return [level.level.name for level in self.levels_rel]

    @property
    def city(self) -> str:
        return self.city_rel.name if self.city_rel else ""

    @property
    def region(self) -> str | None:
        return (
            self.city_rel.region.name
            if self.city_rel and self.city_rel.region
            else None
        )

    @property
    def country(self) -> str | None:
        return (
            self.city_rel.region.country.name
            if self.city_rel and self.city_rel.region and self.city_rel.region.country
            else None
        )
