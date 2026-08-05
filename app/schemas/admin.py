from __future__ import annotations

from datetime import datetime
from app.schemas.level import LevelRead
from app.schemas.style import StyleRead

from pydantic import BaseModel, ConfigDict

from app.schemas.locations import LocationBase


class AdminLocationBase(LocationBase):
    pass

class AdminLocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_ids: list[int] = Field(default_factory=list)
    styles: list[StyleRead] = Field(default_factory=list)
    levels: list[LevelRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminLocationCreate(AdminLocationBase):
    model_config = ConfigDict(from_attributes=True)

    activity_ids: list[int] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)


class AdminLocationListResponse(BaseModel):
    items: list[AdminLocationRead]
    total: int
    limit: int
    offset: int
