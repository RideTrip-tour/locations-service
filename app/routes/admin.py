from fastapi import APIRouter, status

from app.routes.query_params import (
    ActivityIdQuery,
    LimitQuery,
    LocationIdPath,
    LocationServiceDep,
    OffsetQuery,
    ReferenceServiceDep,
    SearchQuery,
    StringListQuery,
    _split_query_values,
)
from app.schemas.admin import (
    AdminCityCreate,
    AdminCityUpdate,
    AdminLocationCreate,
    AdminLocationListResponse,
    AdminLocationRead,
    AdminReferenceCreate,
    AdminRegionCreate,
    AdminRegionUpdate,
)
from app.schemas.locations import LocationFilterOptions
from app.schemas.references import ReferenceLocationsResponse, ReferenceRead

router = APIRouter(prefix="/api/admin/locations", tags=["Admin Locations"])


@router.get("/", response_model=AdminLocationListResponse)
async def get_list_locations(
    service: LocationServiceDep,
    search: SearchQuery = None,
    region: StringListQuery = None,
    city: StringListQuery = None,
    country: StringListQuery = None,
    activity_id: ActivityIdQuery = None,
    styles: StringListQuery = None,
    levels: StringListQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Return locations using multi-value filters with OR inside each field."""
    return await service.list_all_locations(
        search=search,
        region=_split_query_values(region, max_length=255),
        city=_split_query_values(city, max_length=255),
        country=_split_query_values(country, max_length=120),
        activity_id=activity_id,
        styles=_split_query_values(styles, max_length=120),
        levels=_split_query_values(levels, max_length=120),
        limit=limit,
        offset=offset,
    )


@router.get("/filters", response_model=LocationFilterOptions)
async def read_location_filters(
    service: LocationServiceDep,
):
    return await service.list_filter_options()


@router.get("/{location_id}", response_model=AdminLocationRead)
async def read_location(
    location_id: LocationIdPath,
    service: LocationServiceDep,
):
    return await service.get_location_for_admin(location_id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AdminLocationRead)
async def create_location(
    service: LocationServiceDep, location_data: AdminLocationCreate
) -> AdminLocationRead:
    return await service.admin_create_location(location_data)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location_by_id(service: LocationServiceDep, location_id: int):
    await service.admin_delete_location(location_id)


admin_references_router = APIRouter(
    prefix="/api/admin/references", tags=["Admin References"]
)


@admin_references_router.get(
    "/styles/{style_id}/locations", response_model=ReferenceLocationsResponse
)
async def read_style_locations(
    style_id: int,
    service: ReferenceServiceDep,
    is_active: bool | None = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Return a paginated list of locations linked to a style, optionally filtered by is_active."""
    return await service.list_style_locations(
        style_id, is_active=is_active, limit=limit, offset=offset
    )


@admin_references_router.get(
    "/levels/{level_id}/locations", response_model=ReferenceLocationsResponse
)
async def read_level_locations(
    level_id: int,
    service: ReferenceServiceDep,
    is_active: bool | None = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Return a paginated list of locations linked to a level, optionally filtered by is_active."""
    return await service.list_level_locations(
        level_id, is_active=is_active, limit=limit, offset=offset
    )


@admin_references_router.post("/styles", status_code=status.HTTP_201_CREATED)
async def create_style(
    service: ReferenceServiceDep, style_data: AdminReferenceCreate
) -> ReferenceRead:
    return await service.admin_create_style(style_data.name)


@admin_references_router.post("/levels", status_code=status.HTTP_201_CREATED)
async def create_levels(
    service: ReferenceServiceDep, level_data: AdminReferenceCreate
) -> ReferenceRead:
    return await service.admin_create_level(level_data.name)


@admin_references_router.post("/countries", status_code=status.HTTP_201_CREATED)
async def create_countries(
    service: ReferenceServiceDep, country_data: AdminReferenceCreate
) -> ReferenceRead:
    return await service.admin_create_country(name=country_data.name)


@admin_references_router.post("/regions", status_code=status.HTTP_201_CREATED)
async def create_regions(
    service: ReferenceServiceDep, region_data: AdminRegionCreate
) -> ReferenceRead:
    """Create a region linked to an existing country."""
    return await service.admin_create_region(
        name=region_data.name, country_id=region_data.country_id
    )


@admin_references_router.post("/cities", status_code=status.HTTP_201_CREATED)
async def create_cities(
    service: ReferenceServiceDep, city_data: AdminCityCreate
) -> ReferenceRead:
    """Create a city linked to an existing region."""
    return await service.admin_create_city(
        name=city_data.name, region_id=city_data.region_id
    )


@admin_references_router.delete(
    "/styles/{style_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_style_by_id(service: ReferenceServiceDep, style_id: int):
    await service.admin_delete_style(style_id)


@admin_references_router.delete(
    "/levels/{level_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_level_by_id(service: ReferenceServiceDep, level_id: int):
    await service.admin_delete_level(level_id)


@admin_references_router.delete(
    "/countries/{country_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_country_by_id(service: ReferenceServiceDep, country_id: int):
    """Delete a country and its regions and cities (cascade).
    Returns 409 if some of those cities are linked to locations.
    """
    await service.admin_delete_country(country_id)


@admin_references_router.delete(
    "/regions/{region_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_region_by_id(service: ReferenceServiceDep, region_id: int):
    """Delete a region and its cities (cascade).
    Returns 409 if some of those cities are linked to locations.
    """
    await service.admin_delete_region(region_id)


@admin_references_router.delete(
    "/cities/{city_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_city_by_id(service: ReferenceServiceDep, city_id: int):
    """Delete a city. Returns 409 if it is linked to a location."""
    await service.admin_delete_city(city_id)


@admin_references_router.patch("/styles/{style_id}", status_code=status.HTTP_200_OK)
async def update_style_by_id(
    service: ReferenceServiceDep,
    style_id: int,
    style_data: AdminReferenceCreate,
) -> ReferenceRead:
    return await service.admin_update_style(item_id=style_id, name=style_data.name)


@admin_references_router.patch("/levels/{level_id}", status_code=status.HTTP_200_OK)
async def update_level_by_id(
    service: ReferenceServiceDep,
    level_id: int,
    level_data: AdminReferenceCreate,
) -> ReferenceRead:
    return await service.admin_update_level(item_id=level_id, name=level_data.name)


@admin_references_router.patch(
    "/countries/{country_id}", status_code=status.HTTP_200_OK
)
async def update_country_by_id(
    service: ReferenceServiceDep,
    country_id: int,
    country_data: AdminReferenceCreate,
) -> ReferenceRead:
    return await service.admin_update_country(
        item_id=country_id, name=country_data.name
    )


@admin_references_router.patch("/regions/{region_id}", status_code=status.HTTP_200_OK)
async def update_region_by_id(
    service: ReferenceServiceDep,
    region_id: int,
    region_data: AdminRegionUpdate,
) -> ReferenceRead:
    """Update a region; when country_id is provided, the region is moved to that country."""
    return await service.admin_update_region(
        item_id=region_id, name=region_data.name, country_id=region_data.country_id
    )


@admin_references_router.patch("/cities/{city_id}", status_code=status.HTTP_200_OK)
async def update_city_by_id(
    service: ReferenceServiceDep,
    city_id: int,
    city_data: AdminCityUpdate,
) -> ReferenceRead:
    """Update a city; when region_id is provided, the city is moved to that region."""
    return await service.admin_update_city(
        item_id=city_id, name=city_data.name, region_id=city_data.region_id
    )
