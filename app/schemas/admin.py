from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from geojson_pydantic import Feature, FeatureCollection, MultiPolygon, Polygon
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.locations import LocationBase
from app.schemas.mixins import PaginationMixin
from app.schemas.references import ReferenceBase, ReferenceRead

RegionBorder = FeatureCollection[Feature[Polygon | MultiPolygon, dict]]


class AdminLocationBase(LocationBase):
    pass


class AdminLocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    distance_to_city_km: Decimal | None = Field(
        default=None, ge=0, decimal_places=3, examples=["0.000"]
    )
    city: str = Field(min_length=1, max_length=150)
    region: str | None = Field(default=None, max_length=150)
    country: str | None = Field(default=None, max_length=150)
    created_at: datetime
    updated_at: datetime


class AdminLocationCreate(AdminLocationBase):
    model_config = ConfigDict(from_attributes=True)


class AdminLocationListResponse(PaginationMixin, BaseModel):
    items: list[AdminLocationRead]


class AdminLocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    city_id: int | None = Field(default=None, ge=1)
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    activity_ids: list[int] | None = Field(default=None)
    styles: list[str] | None = Field(default=None)
    levels: list[str] | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @model_validator(mode="after")
    def check_coords_pair(self):
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None
        if has_lat != has_lon:
            raise ValueError("latitude and longitude must be provided together")
        return self


class AdminReferenceCreate(ReferenceBase):
    pass


class AdminRegionCreate(ReferenceBase):
    country_id: int
    border: RegionBorder = Field(
        description="GeoJSON FeatureCollection от geojson.io. Doc for FeatureCollection, https://turfjs.org/docs/api/featureCollection."
    )


class AdminCityCreate(ReferenceBase):
    region_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AdminRegionUpdate(ReferenceBase):
    country_id: int | None = None


class AdminCityUpdate(ReferenceBase):
    region_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class AdminCityRead(ReferenceRead):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AdminCityListResponse(PaginationMixin):
    items: list[AdminCityRead]
