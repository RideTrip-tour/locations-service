import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.crud.locations import (  # noqa E402
    admin_create_location,
    apply_location_filters,
    list_location_filter_options,
)
from app.db.models import Location
from app.routes.query_params import (
    _parse_activity_ids,
    _parse_location_id,
    _split_query_values,
)
from app.routes.locations import (
    read_locations,
    router,
)
from app.services.locations import LocationService


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, statement):
        raise AssertionError("FakeSession.execute should be monkeypatched")

    def add(self, obj):
        raise AssertionError("FakeSession.add should be monkeypatched")

    async def refresh(self, obj, attribute_names=None):
        raise AssertionError("FakeSession.refresh should be monkeypatched")


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


def test_get_location_raises_not_found(monkeypatch):
    session = FakeSession()
    service = LocationService(session)

    async def fake_get_location_by_id(db, location_id, *, only_active=True):
        assert only_active is True

    monkeypatch.setattr(
        "app.services.locations.get_location_by_id", fake_get_location_by_id
    )

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

    monkeypatch.setattr(
        "app.services.locations.get_location_by_id", fake_get_location_by_id
    )

    result = asyncio.run(service.get_location_for_admin(1))

    assert result.id == 1
    assert result.is_active is False


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
            service=service,
        )
    )

    assert service.kwargs["region"] == ["Краснодарский край", "Карачаево-Черкесия"]
    assert service.kwargs["activity_id"] == [12, 15]
    assert service.kwargs["styles"] == ["ski", "freeride"]


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
    assert _split_query_values(["ski, freeride", "mountain"]) == [
        "ski",
        "freeride",
        "mountain",
    ]
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
    activity_id_schema = next(
        parameter["schema"]
        for parameter in parameters
        if parameter["name"] == "activity_id"
    )

    assert activity_id_schema["anyOf"][0]["type"] == "array"
    assert activity_id_schema["anyOf"][0]["items"]["type"] == "integer"


def test_apply_location_filters_uses_case_insensitive_filters_and_exists():
    statement = apply_location_filters(
        select(Location),
        region=["Краснодарский край", "Карачаево-Черкесия"],
        activity_id=[1, 2],
        styles=["mountain"],
        levels=["Любитель"],
        is_active=True,
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "lower(locations.region) IN" in compiled
    assert "location_activities" in compiled
    assert "location_styles" in compiled
    assert "styles" in compiled
    assert "lower(styles.name) IN" in compiled
    assert "location_levels" in compiled
    assert "levels" in compiled
    assert "lower(levels.name) IN" in compiled
    assert "locations.is_active IS true" in compiled
    assert " AND " in compiled


def test_apply_style_filter_joins_styles():
    statement = apply_location_filters(
        select(Location),
        styles=["mountain", "freeride"],
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_styles" in compiled
    assert "styles" in compiled
    assert "styles.id = location_styles.style_id" in compiled
    assert "lower(styles.name) IN" in compiled


def test_apply_level_filter_joins_levels():
    statement = apply_location_filters(
        select(Location),
        levels=["Любитель"],
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_levels" in compiled
    assert "levels" in compiled
    assert "levels.id = location_levels.level_id" in compiled
    assert "lower(levels.name) IN" in compiled


def test_apply_location_filters_empty_activity_ids_match_no_locations():
    statement = apply_location_filters(select(Location), activity_id=[], is_active=True)

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_activities" not in compiled


def test_apply_location_filters_empty_styles_match_no_locations():
    statement = apply_location_filters(select(Location), styles=[], is_active=True)

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_styles" not in compiled
    assert "styles" not in compiled


def test_apply_location_filters_empty_levels_match_no_locations():
    statement = apply_location_filters(select(Location), levels=[], is_active=True)

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_levels" not in compiled
    assert "levels" not in compiled


def test_apply_location_filters_empty_lists_keep_other_filters():
    statement = apply_location_filters(
        select(Location),
        activity_id=[],
        styles=[],
        levels=[],
        is_active=False,
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "location_activities" not in compiled
    assert "location_styles" not in compiled
    assert "location_levels" not in compiled
    assert "locations.is_active IS false" in compiled


def test_list_location_filter_options_joins_name_tables(monkeypatch):
    session = FakeSession()

    async def fake_execute(statement):
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        if "styles" in compiled:
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: ["mountain", "freeride"])
            )
        if "levels" in compiled:
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: ["beginner"])
            )
        if "location_activities" in compiled:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [12]))
        if "locations.region" in compiled:
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: ["Краснодарский край"])
            )
        if "locations.city" in compiled:
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: ["Сочи"])
            )
        if "locations.country" in compiled:
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: ["Russia"])
            )
        raise AssertionError(f"unexpected statement: {compiled}")

    monkeypatch.setattr(session, "execute", fake_execute)

    result = asyncio.run(list_location_filter_options(session))

    assert result["styles"] == ["mountain", "freeride"]
    assert result["levels"] == ["beginner"]
    assert result["activity_ids"] == [12]


def test_admin_create_location_links_styles_and_levels(monkeypatch):
    session = FakeSession()
    location_in = SimpleNamespace(
        model_dump=lambda exclude_unset: {
            "name": "Роза Хутор",
            "region": "Краснодарский край",
            "activity_ids": [12],
            "styles": ["mountain"],
            "levels": ["beginner"],
        }
    )

    style = SimpleNamespace(id=1)
    level = SimpleNamespace(id=2)

    async def fake_execute(statement):
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        if "styles" in compiled:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))
        if "levels" in compiled:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [level]))
        raise AssertionError(f"unexpected statement: {compiled}")

    monkeypatch.setattr(session, "execute", fake_execute)
    monkeypatch.setattr(session, "add", lambda obj: None)
    monkeypatch.setattr(session, "commit", session.commit)

    async def fake_refresh(obj, attribute_names=None):
        return None

    monkeypatch.setattr(session, "refresh", fake_refresh)

    result = asyncio.run(admin_create_location(session, location_in))

    assert isinstance(result, Location)
    assert result.styles_rel[0].style_id == 1
    assert result.levels_rel[0].level_id == 2
    assert session.commits == 1


def test_admin_create_location_with_empty_lists(monkeypatch):
    session = FakeSession()
    location_in = SimpleNamespace(
        model_dump=lambda exclude_unset: {
            "name": "Роза Хутор",
            "region": "Краснодарский край",
            "activity_ids": [],
            "styles": [],
            "levels": [],
        }
    )

    async def fake_execute(statement):
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        if "styles" in compiled:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))
        if "levels" in compiled:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))
        raise AssertionError(f"unexpected statement: {compiled}")

    monkeypatch.setattr(session, "execute", fake_execute)
    monkeypatch.setattr(session, "add", lambda obj: None)
    monkeypatch.setattr(session, "commit", session.commit)

    async def fake_refresh(obj, attribute_names=None):
        return None

    monkeypatch.setattr(session, "refresh", fake_refresh)

    result = asyncio.run(admin_create_location(session, location_in))

    assert isinstance(result, Location)
    assert result.activities_rel == []
    assert result.styles_rel == []
    assert result.levels_rel == []
    assert session.commits == 1
