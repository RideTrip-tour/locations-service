from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.locations import (
    add_favorite_location,
    get_location_by_id,
    list_favorite_location_ids,
    list_favorite_locations,
    list_location_filter_options,
    list_locations,
    remove_favorite_location,
)
from app.db.database import get_async_session
from app.schemas.locations import (
    FavoriteStateResponse,
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)


class LocationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_location(self, location_id: int, user_id: int | None = None) -> LocationRead:
        location = await get_location_by_id(self.session, location_id)
        if location is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        return await self._to_read(location, user_id=user_id)

    async def list_locations(
        self,
        *,
        search: str | None = None,
        region: str | None = None,
        city: str | None = None,
        country: str | None = None,
        activity_id: int | None = None,
        style: str | None = None,
        level: str | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
        user_id: int | None = None,
    ) -> LocationListResponse:
        locations, total = await list_locations(
            self.session,
            search=search,
            region=region,
            city=city,
            country=country,
            activity_id=activity_id,
            style=style,
            level=level,
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
        items = [await self._to_read(location, user_id=user_id, favorite_ids=favorite_ids) for location in locations]
        return LocationListResponse(items=items, total=total, limit=limit, offset=offset)

    async def list_favorites(
        self,
        user_id: int,
        *,
        search: str | None = None,
        region: str | None = None,
        city: str | None = None,
        country: str | None = None,
        activity_id: int | None = None,
        style: str | None = None,
        level: str | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> LocationListResponse:
        locations, total = await list_favorite_locations(
            self.session,
            user_id=user_id,
            search=search,
            region=region,
            city=city,
            country=country,
            activity_id=activity_id,
            style=style,
            level=level,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        items = [await self._to_read(location, user_id=user_id, favorite_ids={location.id}) for location in locations]
        return LocationListResponse(items=items, total=total, limit=limit, offset=offset)

    async def add_favorite(self, location_id: int, user_id: int) -> FavoriteStateResponse:
        location = await get_location_by_id(self.session, location_id)
        if location is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        try:
            await add_favorite_location(self.session, user_id=user_id, location_id=location_id)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Location already in favorites") from exc
        return FavoriteStateResponse(location_id=location_id, is_favorite=True)

    async def remove_favorite(self, location_id: int, user_id: int) -> None:
        removed = await remove_favorite_location(self.session, user_id=user_id, location_id=location_id)
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location favorite not found")
        await self.session.commit()

    async def list_filter_options(self) -> LocationFilterOptions:
        options = await list_location_filter_options(self.session)
        return LocationFilterOptions(**options)

    async def _to_read(
        self,
        location,
        *,
        user_id: int | None = None,
        favorite_ids: set[int] | None = None,
    ) -> LocationRead:
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


async def get_location_service(
    session: AsyncSession = Depends(get_async_session),
) -> LocationService:
    return LocationService(session)
