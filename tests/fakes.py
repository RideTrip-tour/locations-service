"""Shared fakes and factories for service tests."""

from types import SimpleNamespace


class FakeSession:
    """Minimal async session stub. Each method raises unless monkeypatched."""

    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, statement):
        raise AssertionError("FakeSession.execute should be monkeypatched")

    async def scalar(self, statement):
        raise AssertionError("FakeSession.scalar should be monkeypatched")

    def add(self, obj):
        raise AssertionError("FakeSession.add should be monkeypatched")

    async def refresh(self, obj, attribute_names=None):
        raise AssertionError("FakeSession.refresh should be monkeypatched")

    async def delete(self, obj):
        raise AssertionError("FakeSession.delete should be monkeypatched")


def make_reference(model, **overrides):
    """Build a reference-like object (Style/Level) with id and name."""
    payload = {"id": 1, "name": "новичок"}
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_location(**overrides):
    """Build a location-like object with all fields used by LocationRead."""
    country = overrides.pop("country", SimpleNamespace(name="Russia"))
    region = overrides.pop(
        "region", SimpleNamespace(name="Краснодарский край", country=country)
    )
    city_rel = overrides.pop(
        "city_rel", SimpleNamespace(name="Сочи", region=region, country=country)
    )
    payload = {
        "id": 1,
        "slug": "rosa-khutor",
        "name": "Роза Хутор",
        "city_id": 1,
        "city": "Сочи",
        "region": "Краснодарский край",
        "country": "Russia",
        "city_rel": city_rel,
        "description": None,
        "latitude": 43.674,
        "longitude": 40.206,
        "distance_to_city_km": 70,
        "activity_ids": [12],
        "styles": ["mountain"],
        "levels": ["beginner"],
        "is_active": True,
        "created_at": "2026-04-13T00:00:00Z",
        "updated_at": "2026-04-13T00:00:00Z",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)
