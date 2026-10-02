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
    LongitudeQuery,
    LatitudeQuery,
    RadiusQuery
)
from app.schemas.locations import (
    LocationFilterOptions,
    LocationListResponse,
    LocationRead,
    LocationWithinRadius
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


@router.get("/radius", response_model=LocationWithinRadius)
async def read_locations_within_radius(
    service: LocationServiceDep,
    latitude: LatitudeQuery,
    longitude: LongitudeQuery,
    radius: RadiusQuery,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
):
    """Returns a paginated list of locations within the given radius."""
    return await service.list_locations_in_radius(latitude=latitude, longitude=longitude, radius=radius,  limit=limit, offset=offset)


@router.get("/{location_id}", response_model=LocationRead)
async def read_location(
    location_id: LocationIdPath,
    service: LocationServiceDep,
):
    return await service.get_location(location_id)
