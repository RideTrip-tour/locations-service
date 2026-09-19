from __future__ import annotations

from pydantic import BaseModel


class PaginationMixin(BaseModel):
    total: int
    limit: int
    offset: int
