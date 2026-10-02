from fastapi import APIRouter

from app.routes.query_params import (
    LimitQuery,
    OffsetQuery,
    ReferenceIdQuery,
    ReferenceNameQuery,
    ReferenceServiceDep,
    LongitudeQuery,
    LatitudeQuery,
    RadiusQuery
)
from app.schemas.references import ReferenceListResponse, CityWithinRadius

router = APIRouter(prefix="/api/locations/references", tags=["references"])


@router.get("/styles", response_model=ReferenceListResponse)
async def read_styles(
    service: ReferenceServiceDep,
    name: ReferenceNameQuery = None,
    id: ReferenceIdQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    return await service.list_styles(name=name, style_id=id, limit=limit, offset=offset)


@router.get("/levels", response_model=ReferenceListResponse)
async def read_levels(
    service: ReferenceServiceDep,
    name: ReferenceNameQuery = None,
    id: ReferenceIdQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    return await service.list_levels(name=name, list_id=id, limit=limit, offset=offset)


@router.get("/cities", response_model=ReferenceListResponse)
async def read_cities(
    service: ReferenceServiceDep,
    name: ReferenceNameQuery = None,
    id: ReferenceIdQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    return await service.list_cities(name=name, city_id=id, limit=limit, offset=offset)


@router.get("/radius", response_model=CityWithinRadius)
async def read_cities_within_radius(
    service: ReferenceServiceDep,
    latitude: LatitudeQuery,
    longitude: LongitudeQuery,
    radius: RadiusQuery,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Returns a paginated list of cities within the given radius."""
    return await service.list_cities_in_radius(latitude=latitude, longitude=longitude, radius=radius, limit=limit, offset=offset)


@router.get("/regions", response_model=ReferenceListResponse)
async def read_regions(
    service: ReferenceServiceDep,
    name: ReferenceNameQuery = None,
    id: ReferenceIdQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    return await service.list_regions(
        name=name, region_id=id, limit=limit, offset=offset
    )


@router.get("/countries", response_model=ReferenceListResponse)
async def read_countries(
    service: ReferenceServiceDep,
    name: ReferenceNameQuery = None,
    id: ReferenceIdQuery = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    return await service.list_countries(
        name=name, country_id=id, limit=limit, offset=offset
    )
