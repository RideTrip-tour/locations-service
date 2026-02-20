from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.location_mapper import location_to_response

from app.schemas.locations_schemas import LocationCreate, LocationResponse
from app.crud import location_crud 
from app.db.database import (
    get_async_session,
) 

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_location(
    request: Request,  # Добавляем Request, чтобы достать user_id от Middleware
    location_in: LocationCreate,
    db: AsyncSession = Depends(get_async_session),
):
    current_user_id = request.state.user_id

    new_location = await location_crud.create_location(db=db, location_in=location_in)
    return location_to_response(new_location)


@router.get("/", response_model=list[LocationResponse])
async def read_locations(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)
):
    locations = await location_crud.get_locations(db=db, skip=skip, limit=limit)
    return [location_to_response(loc) for loc in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def read_location(
    location_id: int, db: AsyncSession = Depends(get_async_session)
):
    location = await location_crud.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location_to_response(location)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location_route(
    location_id: int, update_data: dict, db: AsyncSession = Depends(get_async_session)
):
    updated_location = await location_crud.update_location(
        db=db, location_id=location_id, update_data=update_data
    )
    if not updated_location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location_to_response(updated_location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location_route(
    location_id: int, db: AsyncSession = Depends(get_async_session)
):
    success = await location_crud.delete_location(db=db, location_id=location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return None
