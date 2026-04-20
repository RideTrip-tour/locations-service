from types import SimpleNamespace
from pathlib import Path
import sys
import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.locations import LocationService # noqa E402


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def make_location(**overrides):
    payload = {
        "id": 1,
        "slug": "rosa-khutor",
        "name": "Роза Хутор",
        "region": "Краснодарский край",
        "city": "Сочи",
        "country": "Russia",
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


@pytest.mark.parametrize("user_id,expected_favorite", [(None, False), (7, True)])
def test_get_location_marks_favorite(monkeypatch, user_id, expected_favorite):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id):
        assert db is session
        assert location_id == 1
        return make_location()

    async def fake_list_favorite_location_ids(db, *, user_id, location_ids):
        assert db is session
        assert user_id == 7
        assert location_ids == [1]
        return {1}

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)
    monkeypatch.setattr(
        "app.services.locations.list_favorite_location_ids",
        fake_list_favorite_location_ids,
    )

    result = asyncio.run(service.get_location(1, user_id=user_id))

    assert result.id == 1
    assert result.is_favorite is expected_favorite


def test_get_location_raises_not_found(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id):
        return None

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_location(1))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Location not found"


def test_list_locations_enriches_favorites(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1)

    async def fake_list_locations(db, **kwargs):
        assert db is session
        assert kwargs["activity_id"] == 12
        return [location], 1

    async def fake_list_favorite_location_ids(db, *, user_id, location_ids):
        assert db is session
        assert user_id == 7
        assert location_ids == [1]
        return {1}

    monkeypatch.setattr("app.services.locations.list_locations", fake_list_locations)
    monkeypatch.setattr(
        "app.services.locations.list_favorite_location_ids",
        fake_list_favorite_location_ids,
    )

    result = asyncio.run(
        service.list_locations(user_id=7, activity_id=12, limit=20, offset=0)
    )

    assert result.total == 1
    assert result.items[0].is_favorite is True


def test_list_locations_without_user_does_not_load_favorites(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1)

    async def fake_list_locations(db, **kwargs):
        return [location], 1

    async def fake_list_favorite_location_ids(*args, **kwargs):
        raise AssertionError("should not load favorites without user_id")

    monkeypatch.setattr("app.services.locations.list_locations", fake_list_locations)
    monkeypatch.setattr(
        "app.services.locations.list_favorite_location_ids",
        fake_list_favorite_location_ids,
    )

    result = asyncio.run(service.list_locations(user_id=None))

    assert result.items[0].is_favorite is False


def test_list_favorites_uses_favorite_query(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1)

    async def fake_list_favorite_locations(db, **kwargs):
        assert db is session
        assert kwargs["user_id"] == 7
        return [location], 1

    monkeypatch.setattr("app.services.locations.list_favorite_locations", fake_list_favorite_locations)

    result = asyncio.run(service.list_favorites(user_id=7))

    assert result.total == 1
    assert result.items[0].is_favorite is True


def test_add_favorite_commits(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id):
        return make_location(id=location_id)

    async def fake_add_favorite_location(db, *, user_id, location_id):
        assert db is session
        assert user_id == 7
        assert location_id == 1
        return SimpleNamespace(id=1)

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)
    monkeypatch.setattr(
        "app.services.locations.add_favorite_location",
        fake_add_favorite_location,
    )

    result = asyncio.run(service.add_favorite(1, 7))

    assert result.location_id == 1
    assert result.is_favorite is True
    assert session.commits == 1
    assert session.rollbacks == 0


def test_add_favorite_rolls_back_on_integrity_error(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id):
        return make_location(id=location_id)

    async def fake_add_favorite_location(db, *, user_id, location_id):
        raise IntegrityError("stmt", {}, Exception("duplicate"))

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)
    monkeypatch.setattr(
        "app.services.locations.add_favorite_location",
        fake_add_favorite_location,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.add_favorite(1, 7))

    assert exc_info.value.status_code == 409
    assert session.commits == 0
    assert session.rollbacks == 1


def test_remove_favorite_raises_not_found(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_remove_favorite_location(db, *, user_id, location_id):
        return False

    monkeypatch.setattr(
        "app.services.locations.remove_favorite_location",
        fake_remove_favorite_location,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.remove_favorite(1, 7))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Location favorite not found"


def test_list_filter_options(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_list_location_filter_options(db):
        assert db is session
        return {
            "regions": ["Краснодарский край"],
            "cities": ["Сочи"],
            "countries": ["Russia"],
            "activity_ids": [12],
            "styles": ["mountain"],
            "levels": ["beginner"],
        }

    monkeypatch.setattr(
        "app.services.locations.list_location_filter_options",
        fake_list_location_filter_options,
    )

    result = asyncio.run(service.list_filter_options())

    assert result.activity_ids == [12]
