from __future__ import annotations

from app.db.models import Location
from app.schemas.locations_schemas import TripFilters


class LocationCompatibilityService:
    @staticmethod
    def check(location: Location, filters: TripFilters) -> tuple[str, str | None]:
        if filters.date_from and location.season_start_month and location.season_end_month:
            month = filters.date_from.month
            if not (location.season_start_month <= month <= location.season_end_month):
                return "incompatible", "Дата поездки вне сезона для локации"

        if filters.transport == "air" and not location.has_airport:
            return "incompatible", "Нет аэропорта рядом"

        return "compatible", None
