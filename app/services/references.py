from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.references import (
    admin_create_reference,
    admin_delete_reference,
    admin_update_reference,
    get_city_names_by_country,
    get_city_names_by_region,
    get_reference_by_id,
    list_cities_with_coords,
    list_cities_within_radius,
    list_locations_by_reference,
    list_references,
)
from app.crud.references import list_cities as crud_list_cities
from app.crud.references import list_regions as crud_list_regions
from app.db.database import get_async_session
from app.db.models import (
    City,
    Country,
    Level,
    LocationLevel,
    LocationStyle,
    Region,
    Style,
)
from app.schemas.admin import AdminCityListResponse, AdminCityRead, RegionBorder
from app.schemas.locations import LocationRead
from app.schemas.references import (
    CityWithinRadius,
    ReferenceListResponse,
    ReferenceLocationsResponse,
    ReferenceRead,
)
from app.services.common import integrity_error_to_http, map_fk_violation_to_http
from app.types import JunctionT, ModelT
from app.utils.geo import featurecollection_to_wkt_element, make_coords

logger = logging.getLogger("location_service")


class ReferenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_reference_or_404(self, model: type[ModelT], item_id: int) -> ModelT:
        """Get reference by ID or raise 404."""
        reference = await get_reference_by_id(
            self.session, model=model, item_id=item_id
        )
        if reference is None:
            logger.warning("%s with id %s not found", model.__name__, item_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} with id {item_id} not found",
            )
        return reference

    async def list_styles(
        self,
        *,
        name: str | None = None,
        style_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        return await self._list_references(
            model=Style, name=name, item_id=style_id, limit=limit, offset=offset
        )

    async def list_levels(
        self,
        *,
        name: str | None = None,
        list_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        return await self._list_references(
            model=Level, name=name, item_id=list_id, limit=limit, offset=offset
        )

    async def list_cities(
        self,
        *,
        region_id: int | None = None,
        name: str | None = None,
        city_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        items, total = await crud_list_cities(
            self.session,
            region_id=region_id,
            name=name,
            item_id=city_id,
            limit=limit,
            offset=offset,
        )
        return ReferenceListResponse(
            items=[ReferenceRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def admin_cities_list(
        self,
        *,
        region_id: int | None = None,
        name: str | None = None,
        city_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        return await self._list_cities_with_coords(
            region_id=region_id, name=name, item_id=city_id, limit=limit, offset=offset
        )

    async def list_cities_in_radius(
        self,
        *,
        region_id: int | None = None,
        latitude: float,
        longitude: float,
        radius: float,
        limit: int = 20,
        offset: int = 0,
    ) -> CityWithinRadius:
        cities, total = await list_cities_within_radius(
            self.session,
            region_id=region_id,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit,
            offset=offset,
        )
        return CityWithinRadius(
            total=total, limit=limit, offset=offset, radius=radius, items=cities
        )

    async def list_regions(
        self,
        *,
        country_id: int | None = None,
        name: str | None = None,
        region_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReferenceListResponse:
        items, total = await crud_list_regions(
            self.session,
            country_id=country_id,
            name=name,
            item_id=region_id,
            limit=limit,
            offset=offset,
        )
        return ReferenceListResponse(
            items=[ReferenceRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def list_countries(
        self,
        *,
        name: str | None = None,
        country_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        return await self._list_references(
            model=Country, name=name, item_id=country_id, limit=limit, offset=offset
        )

    async def _list_references(
        self,
        model: type[ModelT],
        *,
        name: str | None = None,
        item_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReferenceListResponse:
        items, total = await list_references(
            self.session,
            model=model,
            name=name,
            item_id=item_id,
            limit=limit,
            offset=offset,
        )
        return ReferenceListResponse(
            items=[ReferenceRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def _list_cities_with_coords(
        self,
        *,
        region_id: int | None = None,
        name: str | None = None,
        item_id: int | list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> AdminCityListResponse:
        items, total = await list_cities_with_coords(
            self.session,
            region_id=region_id,
            name=name,
            item_id=item_id,
            limit=limit,
            offset=offset,
        )
        return AdminCityListResponse(
            items=[AdminCityRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def admin_create_style(
        self,
        name: str,
    ) -> ReferenceRead:
        return await self._create_reference(model=Style, name=name)

    async def admin_create_level(
        self,
        name: str,
    ) -> ReferenceRead:
        return await self._create_reference(model=Level, name=name)

    async def admin_create_country(self, name: str) -> ReferenceRead:
        return await self._create_reference(model=Country, name=name)

    async def admin_create_region(
        self, name: str, country_id: int, border: RegionBorder
    ) -> ReferenceRead:
        """Create a region linked to a country."""
        border_element = None
        if border:
            try:
                border_element = featurecollection_to_wkt_element(border)
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid GeoJSON: {exc}",
                )
        try:
            item = await admin_create_reference(
                self.session,
                model=Region,
                name=name,
                country_id=country_id,
                border=border_element,
            )
        except IntegrityError as exc:
            raise integrity_error_to_http(
                exc=exc,
                action="creation",
                item_name=name,
                base_model=Region,
                parent_id=country_id,
                parent_model=Country,
            ) from exc
        return ReferenceRead.model_validate(item)

    async def admin_create_city(
        self, name: str, region_id: int, latitude: float, longitude: float
    ) -> AdminCityRead:
        """Create a city linked to a region."""
        try:
            item = await admin_create_reference(
                self.session,
                model=City,
                name=name,
                region_id=region_id,
                coords=make_coords(latitude=latitude, longitude=longitude),
            )
        except IntegrityError as exc:
            raise integrity_error_to_http(
                exc=exc,
                action="creation",
                item_name=name,
                base_model=City,
                parent_id=region_id,
                parent_model=Region,
            ) from exc
        return AdminCityRead.model_validate(item)

    async def _create_reference(self, model: type[ModelT], name: str) -> ReferenceRead:
        try:
            item = await admin_create_reference(self.session, model=model, name=name)
        except IntegrityError as exc:
            raise integrity_error_to_http(
                exc=exc, action="creation", item_name=name, base_model=model
            ) from exc
        logger.info("%s was successfully created", model.__name__)
        return ReferenceRead.model_validate(item)

    async def admin_update_style(self, item_id: int, name: str) -> ReferenceRead:
        return await self._update_reference(model=Style, item_id=item_id, name=name)

    async def admin_update_level(self, item_id: int, name: str) -> ReferenceRead:
        return await self._update_reference(model=Level, item_id=item_id, name=name)

    async def admin_update_city(
        self, item_id: int, name: str, region_id: int | None
    ) -> ReferenceRead:
        fields = {"name": name}
        if region_id is not None:
            fields["region_id"] = region_id
        updated = await self._update_reference(model=City, item_id=item_id, **fields)
        return updated

    async def admin_update_region(
        self, item_id: int, name: str, country_id: int | None
    ) -> ReferenceRead:
        fields = {"name": name}
        if country_id is not None:
            fields["country_id"] = country_id
        updated = await self._update_reference(model=Region, item_id=item_id, **fields)
        return updated

    async def admin_update_country(self, item_id: int, name: str) -> ReferenceRead:
        return await self._update_reference(model=Country, item_id=item_id, name=name)

    async def _update_reference(
        self, model: type[ModelT], item_id: int, **fields
    ) -> ReferenceRead:
        try:
            updated_item = await admin_update_reference(
                self.session, model=model, item_id=item_id, **fields
            )
        except IntegrityError as exc:
            parent_id = fields.get("region_id") or fields.get("country_id")
            raise integrity_error_to_http(
                exc=exc,
                action="update",
                item_name=fields["name"],
                base_model=model,
                parent_id=parent_id,
            ) from exc
        if updated_item is None:
            logger.warning("%s with id %s not found", model.__name__, item_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} with id {item_id} not found",
            )
        logger.info("%s with id %s was successfully updated", model.__name__, item_id)
        return ReferenceRead.model_validate(updated_item)

    async def list_style_locations(
        self,
        style_id: int,
        *,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReferenceLocationsResponse:
        return await self._list_reference_locations(
            model=Style,
            item_id=style_id,
            junction_model=LocationStyle,
            reference_field=LocationStyle.style_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def list_level_locations(
        self,
        level_id: int,
        *,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReferenceLocationsResponse:
        return await self._list_reference_locations(
            model=Level,
            item_id=level_id,
            junction_model=LocationLevel,
            reference_field=LocationLevel.level_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def _list_reference_locations(
        self,
        model: type[ModelT],
        item_id: int,
        junction_model: type[JunctionT],
        reference_field: Any,
        *,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ReferenceLocationsResponse:
        reference = await self._get_reference_or_404(model=model, item_id=item_id)
        locations, total = await list_locations_by_reference(
            self.session,
            item_id=item_id,
            junction_model=junction_model,
            reference_field=reference_field,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        return ReferenceLocationsResponse(
            id=reference.id,
            name=reference.name,
            locations=[LocationRead.model_validate(loc) for loc in locations],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def admin_delete_style(self, style_id: int) -> None:
        await self._delete_reference(model=Style, item_id=style_id)

    async def admin_delete_level(self, level_id: int) -> None:
        await self._delete_reference(model=Level, item_id=level_id)

    async def admin_delete_city(self, city_id: int) -> None:
        try:
            await self._delete_reference(model=City, item_id=city_id)
        except IntegrityError as exc:
            logger.exception(
                "City deletion is failed, city with id %s linked to locations", city_id
            )
            raise map_fk_violation_to_http(
                exc=exc,
                detail="Cannot delete: City is linked to locations. Move or delete those locations first",
            ) from exc

    async def admin_delete_region(self, region_id: int) -> None:
        await self._get_reference_or_404(model=Region, item_id=region_id)
        linked_cities = await get_city_names_by_region(self.session, region_id)
        try:
            await self._delete_reference(model=Region, item_id=region_id)
        except IntegrityError as exc:
            logger.exception(
                "Region deletion is failed, cities linked to locations: %s",
                linked_cities,
            )
            raise map_fk_violation_to_http(
                exc=exc,
                detail=f"Cannot delete: {', '.join(linked_cities)} are linked to locations. Move or delete those locations first",
            ) from exc

    async def admin_delete_country(self, country_id: int) -> None:
        await self._get_reference_or_404(model=Country, item_id=country_id)
        linked_cities = await get_city_names_by_country(self.session, country_id)
        try:
            await self._delete_reference(model=Country, item_id=country_id)
        except IntegrityError as exc:
            logger.exception(
                "Country deletion is failed, cities linked to locations: %s",
                linked_cities,
            )
            raise map_fk_violation_to_http(
                exc=exc,
                detail=f"Cannot delete: {', '.join(linked_cities)} are linked to locations. Move or delete those locations first",
            ) from exc

    async def _delete_reference(self, model: type[ModelT], item_id: int) -> None:
        deleted = await admin_delete_reference(
            self.session, model=model, item_id=item_id
        )
        if not deleted:
            logger.warning(
                "Deletion is failed, %s with id %s not found", model.__name__, item_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} not found",
            )
        logger.info("%s with id %s was successfully deleted", model.__name__, item_id)


def get_reference_service(
    session: AsyncSession = Depends(get_async_session),
) -> ReferenceService:
    return ReferenceService(session)
