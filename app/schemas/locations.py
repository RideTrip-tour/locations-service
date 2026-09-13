from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mixins import PaginationMixin


class LocationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    city_id: int = Field(ge=1)
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_to_city_km: int | None = Field(default=None, ge=0)
    activity_ids: list[int] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
    is_active: bool = True
    slug: str | None = None


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str = Field(min_length=1, max_length=255)
    region: str | None = Field(min_length=1, max_length=255)
    country: str | None = Field(max_length=120)
    created_at: datetime
    updated_at: datetime


class LocationListResponse(PaginationMixin, BaseModel):
    items: list[LocationRead]


class LocationFilterOptions(BaseModel):
    regions: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    activity_ids: list[int] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
