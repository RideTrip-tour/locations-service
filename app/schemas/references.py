from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.locations import LocationRead
from app.schemas.mixins import PaginationMixin


class ReferenceBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class ReferenceRead(ReferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ReferenceListResponse(PaginationMixin, BaseModel):
    items: list[ReferenceRead]


class ReferenceLocationsResponse(PaginationMixin, ReferenceRead):
    locations: list[LocationRead]
