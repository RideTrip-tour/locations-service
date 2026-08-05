from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.crud.locations import (
    admin_create_location,
    admin_delete_location_by_id,
    add_favorite_location,
    get_location_by_id,
    list_favorite_location_ids,
    list_favorite_locations,
    list_location_filter_options,
    list_locations,
    remove_favorite_location,
    get_existing_values,
)
from app.db.database import get_async_session
from app.db.models import Activity, Style, Level
from app.schemas.admin import AdminLocationCreate, AdminLocationRead
from app.schemas.locations import (
    FavoriteStateResponse,
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
        self, location_id: int, user_id: int | None = None
    ) -> LocationRead:
        location = await self._get_location(location_id)
        return await self._to_read(location, user_id=user_id)

    async def get_location_for_admin(
        self, location_id: int, user_id: int | None = None
    ) -> LocationRead:
        location = await self._get_location(location_id, only_active=False)
        return await self._to_read(location, user_id=user_id)

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
        user_id: int | None = None,
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
            user_id=user_id,
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
        user_id: int | None = None,
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
            user_id=user_id,
        )

    async def list_favorites(
        self,
        user_id: int,
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
        """List current user's favorite locations with the shared location filters."""
        locations, total = await list_favorite_locations(
            self.session,
            user_id=user_id,
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
        items = [
            await self._to_read(location, user_id=user_id, favorite_ids={location.id})
            for location in locations
        ]
        return LocationListResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def add_favorite(
        self, location_id: int, user_id: int
    ) -> FavoriteStateResponse:
        await self._get_location(location_id, only_active=True)
        try:
            await add_favorite_location(
                self.session, user_id=user_id, location_id=location_id
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Location already in favorites",
            ) from exc
        return FavoriteStateResponse(location_id=location_id, is_favorite=True)

    async def remove_favorite(self, location_id: int, user_id: int) -> None:
        removed = await remove_favorite_location(
            self.session, user_id=user_id, location_id=location_id
        )
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location favorite not found",
            )
        await self.session.commit()

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

    async def _validate_filter_exists(
            self,
            column: InstrumentedAttribute,
            values: list = None,
            *,
            label: str
    ) -> None:
        if not values:
            return
        if not isinstance(values, list):
            values = [values]
        found = await get_existing_values(self.session, column, values)
        missing = set(values) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{label} not found! Missing values: {sorted(missing)}"
            )

    async def _validate_filters_exists(
            self,
            activity_ids: list[int],
            styles: list[str],
            levels: list[str],
    ) -> None:
        await self._validate_filter_exists(Activity.id, activity_ids, label="Activities")
        await self._validate_filter_exists(Style.id, styles, label="Styles")
        await self._validate_filter_exists(Level.id, levels, label="Levels")

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
        user_id: int | None = None,
    ) -> LocationListResponse:
        await self._validate_filters_exists(activity_id, styles, levels)

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
        favorite_ids: set[int] = set()
        if user_id is not None and locations:
            favorite_ids = await list_favorite_location_ids(
                self.session,
                user_id=user_id,
                location_ids=[location.id for location in locations],
            )
        items = [
            await self._to_read(location, user_id=user_id, favorite_ids=favorite_ids)
            for location in locations
        ]
        return LocationListResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def _to_read(
        self,
        location,
        *,
        user_id: int | None = None,
        favorite_ids: set[int] | None = None,
    ) -> LocationRead:
        """Convert a location model to an API schema and enrich it with favorite state."""
        read = LocationRead.model_validate(location)
        if user_id is not None:
            if favorite_ids is None:
                favorite_ids = await list_favorite_location_ids(
                    self.session,
                    user_id=user_id,
                    location_ids=[location.id],
                )
            read = read.model_copy(update={"is_favorite": location.id in favorite_ids})
        return read

    async def admin_create_location(
        self, location_in: AdminLocationCreate
    ) -> AdminLocationRead:
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
