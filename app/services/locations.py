from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.locations import (
    admin_create_location,
    admin_delete_location_by_id,
    admin_update_location,
    get_location_by_id,
    get_reference_options,
    list_location_filter_options,
    list_locations,
)
from app.db.database import get_async_session
from app.exceptions import CityNotFoundError
from app.schemas.admin import (
    AdminLocationCreate,
    AdminLocationRead,
    AdminLocationUpdate,
)
from app.schemas.locations import (
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)

StrFilter = str | list[str]
IntFilter = int | list[int]

logger = logging.getLogger("location_service")

LOCATION_NOT_FOUND = "Location not found"


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
            logger.warning("Location with id: %s not found", location_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=LOCATION_NOT_FOUND
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
    def _missing_values(requested: list, existing: set[str] | set[int]) -> list:
        """Return values that are not present among the existing ones."""
        return [value for value in requested if value not in existing]

    async def _ensure_relations_exist(
        self, location_in: AdminLocationCreate | AdminLocationUpdate
    ) -> None:
        """Raise 422 if any requested activity, style or level is not yet in the DB."""
        relation_fields = {"styles", "levels"} & location_in.model_fields_set
        if not relation_fields:
            return
        options = await get_reference_options(self.session)

        missing = {
            field: self._missing_values(getattr(location_in, field), options[field])
            for field in relation_fields
        }
        missing = {field: values for field, values in missing.items() if values}
        if missing:
            logger.warning("Creation is failed, missing relations: %s", missing)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=missing
            )

    async def admin_create_location(
        self, location_in: AdminLocationCreate
    ) -> AdminLocationRead:
        await self._ensure_relations_exist(location_in)

        try:
            location = await admin_create_location(self.session, location_in)
        except CityNotFoundError as e:
            logger.warning(
                "Location creation failed, city with id: %s not found", e.city_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with id {e.city_id} not found.",
            ) from e
        logger.info("Location with id %s was successfully created", location.id)
        return AdminLocationRead.model_validate(location)

    async def admin_update_location(
        self, location_id: int, location_in: AdminLocationUpdate
    ) -> AdminLocationRead:
        await self._ensure_relations_exist(location_in)
        try:
            updated_location = await admin_update_location(
                self.session, location_id, location_in
            )
        except CityNotFoundError as e:
            logger.warning(
                "Location update failed, city with id: %s not found", e.city_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with id {e.city_id} not found.",
            ) from e

        if updated_location is None:
            logger.warning("Location with id %s not found for update", location_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=LOCATION_NOT_FOUND
            )
        logger.info("Location with id %s was successfully updated", location_id)
        return AdminLocationRead.model_validate(updated_location)

    async def admin_delete_location(self, location_id: int) -> None:
        deleted = await admin_delete_location_by_id(self.session, location_id)
        if not deleted:
            logger.warning("Location with id %s is not found for deletion", location_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=LOCATION_NOT_FOUND
            )
        logger.info("Location with id %s was successfully deleted", location_id)


def get_location_service(
    session: AsyncSession = Depends(get_async_session),
) -> LocationService:
    return LocationService(session)
