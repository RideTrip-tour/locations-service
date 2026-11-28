import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.celery.app import Celery
from app.publishers.connectors import CeleryConnector
from app.publishers.task_publisher import TaskPublisher
from scripts.seeds import constants as seed_constants
from scripts.seeds import geo_data
from tests.fakes import (
    FakeAsyncConn,
    FakeAsyncEngine,
    FakeGeoDataFrame,
    FakeSyncEngine,
    make_country,
)

COUNTRY_RU = make_country()


@pytest.fixture
def cities_capture(monkeypatch):
    """Prepares mocks for _load_cities and returns captured-container."""

    class Capture:
        def __init__(self):
            self.cities = None
            self.conn = None
            self.rows = None

    cap = Capture()
    cap.conn = FakeAsyncConn(rows=[])

    def fake_to_postgis(self, table, engine, **kwargs):
        cap.rows = self.rows

    monkeypatch.setattr(FakeGeoDataFrame, "to_postgis", fake_to_postgis)
    monkeypatch.setattr(geo_data, "create_engine", lambda url: FakeSyncEngine([]))
    monkeypatch.setattr(
        geo_data, "create_async_engine", lambda url: FakeAsyncEngine(cap.conn)
    )
    monkeypatch.setattr(seed_constants, "cities_shp_path", lambda: "cities.shp")

    def set_cities(rows):
        cap.cities = FakeGeoDataFrame(rows)
        monkeypatch.setattr(geo_data.geopandas, "read_file", lambda p: cap.cities)
        return cap.cities

    cap.set_cities = set_cities
    return cap


@pytest.fixture
def celery_app():
    return MagicMock(spec=Celery)


@pytest.fixture
def celery_connector(celery_app):
    return CeleryConnector(producer=celery_app)


@pytest.fixture
def task_publisher(celery_connector):
    TaskPublisher._instance = None
    publisher = TaskPublisher(connector=celery_connector)
    yield publisher
    TaskPublisher._instance = None


@pytest.fixture
def db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db
