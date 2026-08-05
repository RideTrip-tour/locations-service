from types import SimpleNamespace
from pathlib import Path
import sys
import asyncio

import pytest
from fastapi import HTTPException
from fastapi import FastAPI
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.crud.locations import apply_location_filters  # noqa E402
from app.db.models import Location  # noqa E402
from app.routes.locations import (  # noqa E402
    _parse_activity_ids,
    _parse_location_id,
    _split_query_values,
    read_favorite_locations,
    read_locations,
    router,
)
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

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert db is session
        assert location_id == 1
        assert only_active is True
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

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert only_active is True
        return None

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_location(1))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Location not found"


def test_get_location_for_admin_includes_inactive_locations(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert db is session
        assert location_id == 1
        assert only_active is False
        return make_location(id=location_id, is_active=False)

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)

    result = asyncio.run(service.get_location_for_admin(1))

    assert result.id == 1
    assert result.is_active is False


def test_list_locations_enriches_favorites(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1)

    async def fake_list_locations(db, **kwargs):
        assert db is session
        assert kwargs["activity_id"] == 12
        assert kwargs["is_active"] is True
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


def test_list_locations_passes_multi_value_filters(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1)

    async def fake_list_locations(db, **kwargs):
        assert db is session
        assert kwargs["region"] == ["Краснодарский край", "Карачаево-Черкесия"]
        assert kwargs["styles"] == ["ski", "freeride"]
        assert kwargs["activity_id"] == [12, 15]
        assert kwargs["is_active"] is True
        return [location], 1

    monkeypatch.setattr("app.services.locations.list_locations", fake_list_locations)

    result = asyncio.run(
        service.list_locations(
            region=["Краснодарский край", "Карачаево-Черкесия"],
            styles=["ski", "freeride"],
            activity_id=[12, 15],
        )
    )

    assert result.total == 1


def test_list_all_locations_does_not_filter_by_active_state(monkeypatch):
    session = FakeSession()
    service = LocationService(session)
    location = make_location(id=1, is_active=False)

    async def fake_list_locations(db, **kwargs):
        assert db is session
        assert kwargs["is_active"] is None
        return [location], 1

    monkeypatch.setattr("app.services.locations.list_locations", fake_list_locations)

    result = asyncio.run(service.list_all_locations())

    assert result.total == 1
    assert result.items[0].is_active is False


def test_read_locations_preserves_repeated_query_values():
    service = SimpleNamespace()

    async def fake_list_locations(**kwargs):
        service.kwargs = kwargs
        return SimpleNamespace()

    service.list_locations = fake_list_locations

    asyncio.run(
        read_locations(
            search=None,
            region=["Краснодарский край", "Карачаево-Черкесия"],
            city=None,
            country=None,
            activity_id=[12, 15],
            styles=["ski", "freeride"],
            levels=None,
            limit=20,
            offset=0,
            user_id=None,
            service=service,
        )
    )

    assert service.kwargs["region"] == ["Краснодарский край", "Карачаево-Черкесия"]
    assert service.kwargs["activity_id"] == [12, 15]
    assert service.kwargs["styles"] == ["ski", "freeride"]


def test_read_favorite_locations_passes_route_filters_to_service():
    service = SimpleNamespace()

    async def fake_list_favorites(
        *,
        user_id,
        search,
        region,
        city,
        country,
        activity_id,
        styles,
        levels,
        is_active,
        limit,
        offset,
    ):
        service.kwargs = {
            "user_id": user_id,
            "search": search,
            "region": region,
            "city": city,
            "country": country,
            "activity_id": activity_id,
            "styles": styles,
            "levels": levels,
            "is_active": is_active,
            "limit": limit,
            "offset": offset,
        }
        return SimpleNamespace()

    service.list_favorites = fake_list_favorites

    asyncio.run(
        read_favorite_locations(
            user_id=7,
            service=service,
            search=None,
            region=None,
            city=None,
            country=None,
            activity_id=None,
            styles=["ski, freeride"],
            levels=["Любитель"],
            limit=20,
            offset=0,
            is_active=True,
        )
    )

    assert service.kwargs["user_id"] == 7
    assert service.kwargs["styles"] == ["ski", "freeride"]
    assert service.kwargs["levels"] == ["Любитель"]


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

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert only_active is True
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


def test_add_favorite_rejects_inactive_location(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert only_active is True
        raise HTTPException(status_code=400, detail="Location not found")

    async def fake_add_favorite_location(db, *, user_id, location_id):
        raise AssertionError("should not add inactive location to favorites")

    monkeypatch.setattr("app.services.locations.get_location_by_id", fake_get_location_by_id)
    monkeypatch.setattr(
        "app.services.locations.add_favorite_location",
        fake_add_favorite_location,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.add_favorite(1, 7))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Location not found"
    assert session.commits == 0
    assert session.rollbacks == 0


def test_add_favorite_rolls_back_on_integrity_error(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert only_active is True
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


def test_split_query_values_supports_repeated_and_csv_values():
    assert _split_query_values(["ski, freeride", "mountain"]) == ["ski", "freeride", "mountain"]
    assert _split_query_values(["  "]) is None


def test_split_query_values_rejects_long_values():
    with pytest.raises(HTTPException) as exc_info:
        _split_query_values(["freeride"], max_length=3)

    assert exc_info.value.status_code == 422


def test_parse_activity_ids_supports_repeated_and_csv_values():
    assert _parse_activity_ids(["12, 15", "18"]) == [12, 15, 18]


def test_parse_activity_ids_ignores_values_above_int32():
    assert _parse_activity_ids(["2147483648"]) == []
    assert _parse_activity_ids(["12", "2147483648"]) == [12]


def test_parse_activity_ids_rejects_invalid_values():
    with pytest.raises(ValueError) as exc_info:
        _parse_activity_ids(["12, abc"])

    assert str(exc_info.value) == "activity_id must be an integer"


def test_parse_location_id_rejects_values_above_int32_as_not_found():
    with pytest.raises(HTTPException) as exc_info:
        _parse_location_id("2147483648")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Location not found"


def test_locations_openapi_keeps_activity_id_as_integer_array():
    app = FastAPI()
    app.include_router(router)

    parameters = app.openapi()["paths"]["/api/locations"]["get"]["parameters"]
    activity_id_schema = next(parameter["schema"] for parameter in parameters if parameter["name"] == "activity_id")

    assert activity_id_schema["anyOf"][0]["type"] == "array"
    assert activity_id_schema["anyOf"][0]["items"]["type"] == "integer"


def test_apply_location_filters_uses_case_insensitive_filters_and_array_overlap_for_ids():
    statement = apply_location_filters(
        select(Location),
        region=["Краснодарский край", "Карачаево-Черкесия"],
        activity_id=[1, 2],
        levels=["Любитель"],
        is_active=True,
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "lower(locations.region) IN" in compiled
    assert "JOIN location_activity" in compiled
    assert "JOIN location_level" in compiled
    assert "JOIN levels" in compiled
    assert "lower(" in compiled
    assert "locations.is_active IS true" in compiled
    assert " AND " in compiled
