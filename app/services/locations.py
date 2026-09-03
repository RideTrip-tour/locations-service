from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.locations import (
    admin_create_location,
    admin_delete_location_by_id,
    get_location_by_id,
    list_location_filter_options,
    list_locations,
)
from app.db.database import get_async_session
from app.schemas.admin import AdminLocationCreate, AdminLocationRead
from app.schemas.locations import (
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)

StrFilter = str | list[str]
IntFilter = int | list[int]


class LocationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_location(
        self,
        location_id: int,
    ) -> LocationRead:
        return await self._get_location(location_id)

    async def get_location_for_admin(
        self,
        location_id: int,
    ) -> LocationRead:
        return await self._get_location(location_id, only_active=False)

    async def list_locations(
        self,
        *,
        search: str | None = None,
        region: StrFilter | None = None,
        city: StrFilter | None = None,
        country: StrFilter | None = None,
        activity_id: IntFilter | None = None,
        styles: StrFilter | None = None,
        levels: StrFilter | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> LocationListResponse:
        return await self._list_locations(
            search=search,
            region=region,
            city=city,
            country=country,
            activity_id=activity_id,
            styles=styles,
            levels=levels,
            is_active=True,
            limit=limit,
            offset=offset,
        )

    async def list_all_locations(
        self,
        *,
        search: str | None = None,
        region: StrFilter | None = None,
        city: StrFilter | None = None,
        country: StrFilter | None = None,
        activity_id: IntFilter | None = None,
        styles: StrFilter | None = None,
        levels: StrFilter | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> LocationListResponse:
        return await self._list_locations(
            search=search,
            region=region,
            city=city,
            country=country,
            activity_id=activity_id,
            styles=styles,
            levels=levels,
            is_active=None,
            limit=limit,
            offset=offset,
        )

    async def list_filter_options(self) -> LocationFilterOptions:
        options = await list_location_filter_options(self.session)
        return LocationFilterOptions(**options)

    async def _get_location(self, location_id: int, *, only_active: bool = True):
        location = await get_location_by_id(
            self.session, location_id, only_active=only_active
        )
        if location is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Location not found"
            )
        return location

    async def _list_locations(
        self,
        *,
        search: str | None = None,
        region: StrFilter | None = None,
        city: StrFilter | None = None,
        country: StrFilter | None = None,
        activity_id: IntFilter | None = None,
        styles: StrFilter | None = None,
        levels: StrFilter | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> LocationListResponse:
        locations, total = await list_locations(
            self.session,
            search=search,
            region=region,
            city=city,
            country=country,
            activity_id=activity_id,
            styles=styles,
            levels=levels,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        return LocationListResponse(
            items=locations, total=total, limit=limit, offset=offset
        )

    @staticmethod
    def _missing_values(requested: list, existing: list[str] | list[int]) -> list:
        """Return values that are not present among the existing ones."""
        return [value for value in requested if value not in existing]

    async def _ensure_relations_exist(self, location_in: AdminLocationCreate) -> None:
        """Raise 422 if any requested activity, style or level is not yet in the DB."""
        options = await list_location_filter_options(self.session)
        missing = {
            "activity_ids": self._missing_values(
                location_in.activity_ids, options["activity_ids"]
            ),
            "styles": self._missing_values(location_in.styles, options["styles"]),
            "levels": self._missing_values(location_in.levels, options["levels"]),
        }
        if any(missing.values()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=missing
            )

    async def admin_create_location(
        self, location_in: AdminLocationCreate
    ) -> AdminLocationRead:
        await self._ensure_relations_exist(location_in)
        return await admin_create_location(self.session, location_in)

    async def admin_delete_location(self, location_id: int) -> None:
        deleted = await admin_delete_location_by_id(self.session, location_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )


async def get_location_service(
    session: AsyncSession = Depends(get_async_session),
) -> LocationService:
    return LocationService(session)
