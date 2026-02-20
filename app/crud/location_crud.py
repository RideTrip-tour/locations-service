from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas.locations_schemas import LocationCreate
from app.db.models import Location


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
