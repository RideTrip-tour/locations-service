from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas.locations_schemas import LocationCreate,LocationResponse
from app.db.models import Location


from sqlalchemy import select, and_
from sqlalchemy.sql import func
from geoalchemy2.functions import ST_DWithin
from app.db.models import Location


async def search_locations(
    db: AsyncSession,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    season_month: int | None = None,
    has_airport: bool | None = None,
    has_railway_station: bool | None = None,
    has_bus_station: bool | None = None,
):
    query = select(Location)

    conditions = []

    # 📍 Гео-фильтр
    if latitude and longitude and radius_km:
        point = func.ST_SetSRID(
            func.ST_MakePoint(longitude, latitude),
            4326
        )
        conditions.append(
            ST_DWithin(
                Location.coordinates,
                point,
                radius_km * 1000  # метры
            )
        )

    # 🌤 Фильтр по сезону
    if season_month:
        conditions.append(
            and_(
                Location.season_start_month <= season_month,
                Location.season_end_month >= season_month,
            )
        )

    # 🚆 Транспорт
    if has_airport is not None:
        conditions.append(Location.has_airport == has_airport)

    if has_railway_station is not None:
        conditions.append(Location.has_railway_station == has_railway_station)

    if has_bus_station is not None:
        conditions.append(Location.has_bus_station == has_bus_station)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    return result.scalars().all()

### 1. Создание (Create)
async def create_location(db: AsyncSession, location_in: LocationCreate) -> Location:
    """Создает новую локацию в базе данных."""
    # Распаковываем данные из схемы сразу в модель SQLAlchemy
    location = Location(**location_in.model_dump())

    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


### 2. Чтение одной записи (Read)
async def get_location(db: AsyncSession, location_id: int) -> Location | None:
    """Получает локацию по её ID. Возвращает None, если не найдена."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    return result.scalar_one_or_none()


### 3. Чтение списка (Read Many)
async def get_locations(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Location]:
    """Получает список локаций с пагинацией (skip/limit)."""
    result = await db.execute(select(Location).offset(skip).limit(limit))
    return list(result.scalars().all())


### 4. Обновление (Update)
async def update_location(
    db: AsyncSession, location_id: int, update_data: dict
) -> Location | None:
    """Обновляет существующую локацию. Принимает словарь с измененными полями."""
    db_location = await get_location(db, location_id)

    if not db_location:
        return None  # Если локации нет, возвращаем None

    # Обновляем только те поля, которые переданы в словаре
    for key, value in update_data.items():
        setattr(db_location, key, value)

    await db.commit()
    await db.refresh(db_location)
    return db_location


### 5. Удаление (Delete)
async def delete_location(db: AsyncSession, location_id: int) -> bool:
    """Удаляет локацию по ID. Возвращает True если удалено, False если не найдено."""
    db_location = await get_location(db, location_id)

    if not db_location:
        return False

    await db.delete(db_location)
    await db.commit()
    return True
