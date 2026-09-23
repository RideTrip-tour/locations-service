import sys
from pathlib import Path

import geopandas as gpd
import pytest
import pytest_asyncio
from shapely.geometry import Point, Polygon
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer(
        image="postgis/postgis:16-3.4",
        username="test",
        password="test",
        dbname="test_db",
    )
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def database_url(postgres_container) -> str:
    sync_url = postgres_container.get_connection_url()
    return sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg")


@pytest_asyncio.fixture(scope="session")
async def engine(database_url):
    eng = create_async_engine(database_url, echo=False)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine) as sess:
        await sess.execute(
            text("TRUNCATE countries, regions, cities RESTART IDENTITY CASCADE")
        )
        await sess.commit()
        yield sess


@pytest.fixture(scope="session")
def regions_geojson(tmp_path_factory):
    """Два региона: Москва и Московская область (простой GeoJSON)."""
    tmp = tmp_path_factory.mktemp("regions")
    path = tmp / "regions_ru.geojson"

    moscow = Polygon([(37.4, 55.6), (37.8, 55.6), (37.8, 55.9), (37.4, 55.9)])
    oblast = Polygon([(36.0, 55.0), (39.0, 55.0), (39.0, 56.5), (36.0, 56.5)])

    gdf = gpd.GeoDataFrame(
        {
            "shapeName": ["Moscow", "Moscow Oblast"],
            "shapeISO": ["RU-MOW", "RU-MOS"],
            "shapeID": ["RU-MOW", "RU-MOS"],
            "shapeGroup": ["RUS", "RUS"],
            "shapeType": ["ADM1", "ADM1"],
        },
        geometry=[moscow, oblast],
        crs=4326,
    )
    gdf.to_file(path, driver="GeoJSON")
    return path


@pytest.fixture(scope="session")
def admin1_shp(tmp_path_factory):
    """Natural Earth Admin 1 — русские имена регионов."""
    tmp = tmp_path_factory.mktemp("admin1")
    path = tmp / "ne_10m_admin_1_states_provinces.shp"

    gdf = gpd.GeoDataFrame(
        {
            "admin": ["Russia", "Russia"],
            "iso_3166_2": ["RU-MOW", "RU-MOS"],
            "name_ru": ["Москва", "Московская область"],
        },
        geometry=[Point(0, 0), Point(0, 0)],
        crs=4326,
    )
    gdf.to_file(path)
    return path


@pytest.fixture(scope="session")
def cities_shp(tmp_path_factory):
    """Города: Москва, Химки (Россия) и Алматы (Казахстан)."""
    tmp = tmp_path_factory.mktemp("cities")
    path = tmp / "ne_10m_populated_places.shp"

    gdf = gpd.GeoDataFrame(
        {
            "SOV0NAME": ["Russia", "Russia", "Kazakhstan"],
            "NAME_RU": ["Москва", "Химки", "Алматы"],
            "NAME": ["Moscow", "Khimki", "Almaty"],
        },
        geometry=[
            Point(37.6, 55.75),
            Point(37.4, 55.9),
            Point(76.9, 43.2),
        ],
        crs=4326,
    )
    gdf.to_file(path)
    return path
