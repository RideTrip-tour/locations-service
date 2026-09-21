from __future__ import annotations


class CityNotFoundError(Exception):
    """Raised when a referenced city does not exist."""

    def __init__(self, city_id: int | None):
        self.city_id = city_id
        super().__init__(f"City with id {city_id} not found")
