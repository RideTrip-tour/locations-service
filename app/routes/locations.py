from fastapi import APIRouter

from app.routes.query_params import (
    ActivityIdQuery,
    LimitQuery,
    LocationIdPath,
    LocationServiceDep,
    OffsetQuery,
    SearchQuery,
    StringListQuery,
    _split_query_values,
)
from app.schemas.locations import (
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
)

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=LocationListResponse)
async def read_locations(
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
    return await service.list_locations(
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


@router.get("/{location_id}", response_model=LocationRead)
async def read_location(
    location_id: LocationIdPath,
    service: LocationServiceDep,
):
    return await service.get_location(location_id)
