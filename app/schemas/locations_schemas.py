from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


# Твоя схема для создания (то, что принимаем от клиента)
class LocationCreate(BaseModel):
    type: Literal["hotel", "airport", "resort", "station"]
    name: str
    id_resort: Optional[int] = None
    id_hotel_booking: Optional[int] = None
    id_equipment_rental: Optional[int] = None
    timezone: Optional[str] = None
    description: Optional[str] = None
    coordinates: Optional[str] = None


# Схема для ответа (то, что отдаем клиенту)
class LocationResponse(LocationCreate):
    id: int  # Добавляем обязательный ID из базы данных

    # Очень важная настройка для работы со SQLAlchemy!
    # Она говорит Pydantic, что данные нужно читать из атрибутов ORM-объекта
    model_config = ConfigDict(from_attributes=True)

    # Примечание: если у тебя старая версия Pydantic (v1),
    # вместо model_config нужно написать:
    # class Config:
    #     orm_mode = True
