from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.locations import LocationBase
from app.schemas.mixins import PaginationMixin
from app.schemas.references import ReferenceBase


class AdminLocationBase(LocationBase):
    pass


class AdminLocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str = Field(min_length=1, max_length=150)
    region: str | None = Field(default=None, max_length=150)
    country: str | None = Field(default=None, max_length=150)
    created_at: datetime
    updated_at: datetime


class AdminLocationCreate(AdminLocationBase):
    model_config = ConfigDict(from_attributes=True)


class AdminLocationListResponse(PaginationMixin, BaseModel):
    items: list[AdminLocationRead]


class AdminReferenceCreate(ReferenceBase):
    pass


class AdminRegionCreate(ReferenceBase):
    country_id: int


class AdminCityCreate(ReferenceBase):
    region_id: int


class AdminRegionUpdate(ReferenceBase):
    country_id: int | None = None


class AdminCityUpdate(ReferenceBase):
    region_id: int | None = None
