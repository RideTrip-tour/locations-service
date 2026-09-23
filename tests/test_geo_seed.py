import asyncio
from types import SimpleNamespace

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


def test_to_sync_url_replaces_driver():
    assert (
        seed_constants.to_sync_url("postgresql+asyncpg://u:p@db/x")
        == "postgresql+psycopg2://u:p@db/x"
    )


def test_regions_path_lowercase():
    assert seed_constants.regions_path("RU").name == "regions_ru.geojson"


def test_run_seed_warns_on_empty_countries(caplog):
    with caplog.at_level("WARNING"):
        asyncio.run(geo_data.run_seed("postgresql+asyncpg://db/x", countries=[]))
    assert "No countries to seed." in caplog.text


def test_run_seed_skips_when_already_loaded(monkeypatch, caplog):
    conn = FakeAsyncConn(scalars=[1, 10, 50])

    monkeypatch.setattr(
        geo_data,
        "create_async_engine",
        lambda url: FakeAsyncEngine(conn),
    )

    def fail_download(countries):
        raise AssertionError("download must not be called")

    monkeypatch.setattr(geo_data, "_download_files", fail_download)

    with caplog.at_level("INFO"):
        asyncio.run(geo_data.run_seed("postgresql+asyncpg://db/x", [COUNTRY_RU]))

    assert "already loaded, skipping" in caplog.text


def test_run_seed_calls_steps_in_order(monkeypatch):
    conn = FakeAsyncConn(scalars=[None])
    called = []

    monkeypatch.setattr(
        geo_data,
        "create_async_engine",
        lambda url: FakeAsyncEngine(conn),
    )

    def record_download(countries):
        called.append(("download", len(countries)))

    async def record_country(url, country):
        called.append(("country", country["code"]))

    async def record_regions(url, country):
        called.append(("regions", country["code"]))

    async def record_cities(url, countries):
        called.append(("cities", len(countries)))

    monkeypatch.setattr(geo_data, "_download_files", record_download)
    monkeypatch.setattr(geo_data, "_load_country", record_country)
    monkeypatch.setattr(geo_data, "_load_regions", record_regions)
    monkeypatch.setattr(geo_data, "_load_cities", record_cities)

    kz = make_country(code="KZ", name="Казахстан", name_en="Kazakhstan", gb_open="KAZ")
    asyncio.run(geo_data.run_seed("postgresql+asyncpg://db/x", [COUNTRY_RU, kz]))

    assert called == [
        ("download", 2),
        ("country", "RU"),
        ("regions", "RU"),
        ("country", "KZ"),
        ("regions", "KZ"),
        ("cities", 2),
    ]


def test_run_seed_defaults_to_supported_countries(monkeypatch):
    conn = FakeAsyncConn(scalars=[None])
    seen = []

    monkeypatch.setattr(
        geo_data,
        "create_async_engine",
        lambda url: FakeAsyncEngine(conn),
    )

    def record_download(countries):
        seen.extend(countries)

    async def noop(*_):
        return None

    monkeypatch.setattr(geo_data, "_download_files", record_download)
    monkeypatch.setattr(geo_data, "_load_country", noop)
    monkeypatch.setattr(geo_data, "_load_regions", noop)
    monkeypatch.setattr(geo_data, "_load_cities", noop)

    asyncio.run(geo_data.run_seed("postgresql+asyncpg://db/x"))

    assert seen == seed_constants.SUPPORTED_COUNTRIES


def test_is_in_db_true_when_all_present():
    conn = FakeAsyncConn(scalars=[1, 10, 50])
    assert asyncio.run(geo_data._is_in_db(conn, [COUNTRY_RU])) is True


def test_is_in_db_false_when_country_missing():
    conn = FakeAsyncConn(scalars=[None])
    assert asyncio.run(geo_data._is_in_db(conn, [COUNTRY_RU])) is False


def test_is_in_db_false_when_regions_missing():
    conn = FakeAsyncConn(scalars=[1, 0])
    assert asyncio.run(geo_data._is_in_db(conn, [COUNTRY_RU])) is False


def test_is_in_db_false_when_cities_missing():
    conn = FakeAsyncConn(scalars=[1, 10, 0])
    assert asyncio.run(geo_data._is_in_db(conn, [COUNTRY_RU])) is False


def test_load_country_uses_on_conflict(monkeypatch):
    conn = FakeAsyncConn()
    monkeypatch.setattr(
        geo_data,
        "create_async_engine",
        lambda url: FakeAsyncEngine(conn),
    )

    asyncio.run(geo_data._load_country("postgresql+asyncpg://db/x", COUNTRY_RU))

    sql = conn.log[0][1]
    assert "INSERT INTO countries" in sql
    assert "ON CONFLICT (name) DO NOTHING" in sql
    assert conn.log[0][2] == {"name": "Россия"}


def test_load_regions_merges_russian_names(monkeypatch):
    regions = FakeGeoDataFrame(
        [
            {"shapeISO": "RU-MOW", "shapeName": "Moscow", "geometry": "g1"},
            {"shapeISO": "RU-MOS", "shapeName": "Moscow Oblast", "geometry": "g2"},
        ]
    )
    admin1 = FakeGeoDataFrame(
        [
            {"admin": "Russia", "iso_3166_2": "RU-MOW", "name_ru": "Москва"},
            {
                "admin": "Russia",
                "iso_3166_2": "RU-MOS",
                "name_ru": "Московская область",
            },
        ]
    )

    read_paths = []

    def fake_read(path):
        read_paths.append(str(path))
        if "geojson" in str(path):
            return regions
        return admin1

    monkeypatch.setattr(geo_data.geopandas, "read_file", fake_read)

    conn = FakeAsyncConn()
    monkeypatch.setattr(
        geo_data, "create_async_engine", lambda url: FakeAsyncEngine(conn)
    )
    monkeypatch.setattr(geo_data, "create_engine", lambda url: FakeSyncEngine([]))

    asyncio.run(geo_data._load_regions("postgresql+asyncpg://db/x", COUNTRY_RU))

    assert any("regions_ru.geojson" in p for p in read_paths)
    assert any("ne_10m_admin_1_states_provinces.shp" in p for p in read_paths)
    upsert_sql = next(
        sql
        for kind, sql, _ in conn.log
        if kind == "execute" and "INSERT INTO regions" in sql
    )
    assert "ON CONFLICT (name, country_id) DO UPDATE" in upsert_sql


def test_load_cities_builds_wkt(monkeypatch):
    cities = FakeGeoDataFrame(
        [
            {
                "SOV0NAME": "Russia",
                "NAME_RU": "Москва",
                "NAME": "Moscow",
                "geometry": SimpleNamespace(x=37.6, y=55.75),
            },
        ]
    )

    monkeypatch.setattr(geo_data.geopandas, "read_file", lambda p: cities)
    monkeypatch.setattr(seed_constants, "cities_shp_path", lambda: "cities.shp")
    monkeypatch.setattr(geo_data, "create_engine", lambda url: FakeSyncEngine([]))

    captured = {}

    def fake_to_postgis(self, table, engine, **kwargs):
        captured["rows"] = self.rows

    monkeypatch.setattr(FakeGeoDataFrame, "to_postgis", fake_to_postgis)

    conn = FakeAsyncConn(rows=[])
    monkeypatch.setattr(
        geo_data, "create_async_engine", lambda url: FakeAsyncEngine(conn)
    )

    asyncio.run(geo_data._load_cities("postgresql+asyncpg://db/x", [COUNTRY_RU]))

    assert captured["rows"][0]["coords"] == "POINT(37.6 55.75)"


def test_load_cities_filter_by_country(monkeypatch):
    cities = FakeGeoDataFrame(
        [
            {
                "SOV0NAME": "Russia",
                "NAME_RU": "Москва",
                "NAME": "Moscow",
                "geometry": SimpleNamespace(x=37.6, y=55.75),
            },
            {
                "SOV0NAME": "Kazakhstan",
                "NAME_RU": "Алматы",
                "NAME": "Almaty",
                "geometry": SimpleNamespace(x=76.9, y=43.2),
            },
        ]
    )

    monkeypatch.setattr(geo_data.geopandas, "read_file", lambda p: cities)
    monkeypatch.setattr(seed_constants, "cities_shp_path", lambda: "cities.shp")
    monkeypatch.setattr(geo_data, "create_engine", lambda url: FakeSyncEngine([]))

    captured = {}

    def fake_to_postgis(self, table, engine, **kwargs):
        captured["rows"] = self.rows

    monkeypatch.setattr(FakeGeoDataFrame, "to_postgis", fake_to_postgis)

    conn = FakeAsyncConn(rows=[])
    monkeypatch.setattr(
        geo_data, "create_async_engine", lambda url: FakeAsyncEngine(conn)
    )

    asyncio.run(geo_data._load_cities("postgresql+asyncpg://db/x", [COUNTRY_RU]))

    names = [r["name"] for r in captured["rows"]]
    assert "Москва" in names
    assert "Алматы" not in names


def test_load_cities_uses_distinct_on(monkeypatch):
    cities = FakeGeoDataFrame(
        [
            {
                "SOV0NAME": "Russia",
                "NAME_RU": "Москва",
                "NAME": "Moscow",
                "geometry": SimpleNamespace(x=37.6, y=55.75),
            },
        ]
    )

    monkeypatch.setattr(geo_data.geopandas, "read_file", lambda p: cities)
    monkeypatch.setattr(seed_constants, "cities_shp_path", lambda: "cities.shp")
    monkeypatch.setattr(geo_data, "create_engine", lambda url: FakeSyncEngine([]))

    conn = FakeAsyncConn(rows=[])
    monkeypatch.setattr(
        geo_data, "create_async_engine", lambda url: FakeAsyncEngine(conn)
    )

    asyncio.run(geo_data._load_cities("postgresql+asyncpg://db/x", [COUNTRY_RU]))

    sql = next(
        s for k, s, _ in conn.log if k == "execute" and "INSERT INTO cities" in s
    )
    assert "DISTINCT ON (cs.name, r.id)" in sql
    assert "ST_Contains" in sql
    assert "ON CONFLICT (name, region_id) DO UPDATE" in sql
