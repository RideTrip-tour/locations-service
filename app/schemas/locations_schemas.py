from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class RegionResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CityResponse(BaseModel):
    id: int
    region_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ActivityResponse(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class LevelResponse(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class LocationCreate(BaseModel):
    name: str
    display_name: str | None = None
    location_type: str = "resort"
    timezone: str | None = None
    description: str | None = None
    region_id: int | None = None
    city_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    has_overnight_stay: bool = False
    has_food_service: bool = False
    has_airport: bool = False
    has_railway_station: bool = False
    has_bus_station: bool = False
    season_start_month: int | None = None
    season_end_month: int | None = None
    activity_ids: list[int] = Field(default_factory=list)
    level_ids: list[int] = Field(default_factory=list)


class LocationResponse(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    location_type: str
    timezone: str | None = None
    description: str | None = None
    region_id: int | None = None
    city_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    has_overnight_stay: bool
    has_food_service: bool
    has_airport: bool
    has_railway_station: bool
    has_bus_station: bool
    season_start_month: int | None = None
    season_end_month: int | None = None

    model_config = ConfigDict(from_attributes=True)


class LocationSearchItem(BaseModel):
    id: int
    name: str
    display_name: str | None
    location_type: str
    region: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    description: str | None
    is_favorite: bool = False
    compatibility_status: Literal["compatible", "incompatible", "unknown"] = "unknown"
    compatibility_reason: str | None = None
    distance_from_city_km: float | None = None


class SearchResponse(BaseModel):
    items: list[LocationSearchItem]
    total: int
    page: int
    page_size: int
    view: Literal["list", "map"]


class TripFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    activity_id: int | None = None
    level_id: int | None = None
    style: str | None = None
    duration_days: int | None = None
    budget: int | None = None
    transport: str | None = None


class CompatibilityResponse(BaseModel):
    location_id: int
    status: Literal["compatible", "incompatible", "unknown"]
    reason: str | None = None


class FavoriteActionResponse(BaseModel):
    location_id: int
    is_favorite: bool


class TripConfigSelectionRequest(BaseModel):
    location_id: int


class TripConfigSelectionResponse(BaseModel):
    config_id: int
    location_id: int
    saved_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
