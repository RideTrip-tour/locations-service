import asyncio
import sys
import types
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

# --- test stubs for optional geoalchemy2 dependency in CI ---
if "geoalchemy2" not in sys.modules:
    geoalchemy2 = types.ModuleType("geoalchemy2")

    from sqlalchemy.types import UserDefinedType

    class _Geography(UserDefinedType):
        def __init__(self, *args, **kwargs):
            pass

        def get_col_spec(self, **kw):
            return "GEOGRAPHY"

    geoalchemy2.Geography = _Geography
    sys.modules["geoalchemy2"] = geoalchemy2

if "geoalchemy2.functions" not in sys.modules:
    geoalchemy2_functions = types.ModuleType("geoalchemy2.functions")

    def _st_dwithin(*args, **kwargs):
        return True

    geoalchemy2_functions.ST_DWithin = _st_dwithin
    sys.modules["geoalchemy2.functions"] = geoalchemy2_functions

from app.routes import location_routes as routes
from app.schemas.locations_schemas import TripConfigSelectionRequest, TripFilters


class DummyRequest:
    def __init__(self, user_id=None):
        self.state = SimpleNamespace(user_id=user_id)


@pytest.mark.parametrize(
    "raw, expected",
    [("77", 77), (77, 77), (None, None), ("abc", None)],
)
def test_get_user_id(raw, expected):
    request = DummyRequest(user_id=raw)
    assert routes._get_user_id(request) == expected


def test_require_user_id_raises_without_auth():
    request = DummyRequest(user_id=None)
    with pytest.raises(HTTPException) as exc:
        routes._require_user_id(request)
    assert exc.value.status_code == 401


def test_locations_health():
    result = asyncio.run(routes.locations_health())
    assert result.status == "ok"
    assert result.service == "locations-service"


def test_search_locations_proxy(monkeypatch):
    async def _fake_search_locations(**kwargs):
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "view": "list",
        }

    monkeypatch.setattr(routes.location_crud, "search_locations", _fake_search_locations)

    response = asyncio.run(
        routes.search_locations(request=DummyRequest("42"), db=None, q="arkhyz", page=1)
    )
    assert response["view"] == "list"
    assert response["total"] == 0


def test_compatibility_check_not_found(monkeypatch):
    async def _fake_get_location(db, location_id):
        return None

    monkeypatch.setattr(routes.location_crud, "get_location", _fake_get_location)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.compatibility_check(
                location_id=404,
                trip_filters=TripFilters(date_from=datetime(2026, 7, 1).date()),
                db=None,
            )
        )

    assert exc.value.status_code == 404


def test_save_location_to_trip_config(monkeypatch):
    async def _fake_save(db, user_id, config_id, location_id):
        return SimpleNamespace(location_id=location_id, created_at=datetime(2026, 4, 19, 12, 0, 0))

    monkeypatch.setattr(routes.location_crud, "save_trip_config_location", _fake_save)

    response = asyncio.run(
        routes.save_location_to_trip_config(
            config_id=123,
            payload=TripConfigSelectionRequest(location_id=55),
            request=DummyRequest("99"),
            db=None,
        )
    )

    assert response.config_id == 123
    assert response.location_id == 55
