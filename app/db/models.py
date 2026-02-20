from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from typing import Optional, Any
from geoalchemy2 import Geometry


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)

    id_resort: Mapped[Optional[int]] = mapped_column(Integer)
    id_hotel_booking: Mapped[Optional[int]] = mapped_column(Integer)
    id_equipment_rental: Mapped[Optional[int]] = mapped_column(Integer)
    type: Mapped[Optional[str]] = mapped_column(String(50))
    coordinates: Mapped[Optional[Any]] = mapped_column(Geometry("POINT"))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String)

    def __repr__(self):
        return f"<Location {self.id}: {self.name} ({self.type})>"
