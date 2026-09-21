from fastapi import APIRouter

from app.routes.query_params import (
    LimitQuery,
    OffsetQuery,
    ReferenceIdQuery,
    ReferenceNameQuery,
    ReferenceServiceDep,
)
from app.schemas.references import ReferenceListResponse

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
