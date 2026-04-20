from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LocationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    region: str = Field(min_length=1, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    country: str = Field(default="Russia", max_length=120)
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_to_city_km: int | None = Field(default=None, ge=0)
    activity_ids: list[int] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
    is_active: bool = True


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    is_favorite: bool = False


class LocationListResponse(BaseModel):
    items: list[LocationRead]
    total: int
    limit: int
    offset: int


class LocationFilterOptions(BaseModel):
    regions: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    activity_ids: list[int] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)


class FavoriteStateResponse(BaseModel):
    location_id: int
    is_favorite: bool
