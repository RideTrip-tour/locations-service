import logging
import zipfile

import geopandas
import requests
from geoalchemy2 import Geometry
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.seeds.constants import (
    CITIES_URL,
    DATA_DIR,
    REGIONS_NAMES_URL,
    REGIONS_POLYGON_URL,
    SUPPORTED_COUNTRIES,
    cities_shp_path,
    regions_path,
    regions_shp_path,
    to_sync_url,
)

logger = logging.getLogger("location_service")


async def run_seed(database_url: str, countries: list[dict[str, str]] | None = None):
    if countries is None:
        countries = SUPPORTED_COUNTRIES
    if not countries:
        logger.warning("No countries to seed.")
        return
    enigene = create_async_engine(database_url)
    async with enigene.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        if await _is_in_db(conn, countries):
            logger.info("Geo data already loaded, skipping.")
            return
    _download_files(countries)
    for country in countries:
        await _load_country(database_url, country)
        await _load_regions(database_url, country)
    await _load_cities(database_url, countries)
    logger.info("Geo data was successfully loaded.")


async def _is_in_db(conn, countries: list[dict[str, str]]) -> bool:
    for country in countries:
        exists = await conn.scalar(
            text("SELECT 1 FROM countries WHERE name = :name"),
            {"name": country["name"]},
        )
        if not exists:
            return False
        regions_count = await conn.scalar(
            text("""
                SELECT COUNT(*)
                FROM regions r
                JOIN countries c ON c.id = r.country_id
                WHERE c.name = :name
            """),
            {"name": country["name"]},
        )
        if not regions_count:
            return False
        cities_count = await conn.scalar(
            text("""
                SELECT COUNT(*)
                FROM cities ct
                JOIN regions r ON r.id = ct.region_id
                JOIN countries c ON c.id = r.country_id
                WHERE c.name = :name
            """),
            {"name": country["name"]},
        )
        if not cities_count:
            return False
    return True


def _download_files(countries: list[dict[str, str]]):
    """Download files if they are not in cache."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for country in countries:
        reg_path = regions_path(country["code"])
        if reg_path.exists():
            continue
        url = REGIONS_POLYGON_URL.format(gb_open=country["gb_open"])
        logger.info("Downloading regions for %s...", country["name_en"])
        regions_request = requests.get(url)
        regions_request.raise_for_status()
        reg_path.write_bytes(regions_request.content)

    admin1 = regions_shp_path()
    if not admin1.exists():
        logger.info("Downloading Natural Earth Admin 1...")
        r = requests.get(REGIONS_NAMES_URL)
        r.raise_for_status()
        zip_path = DATA_DIR / "admin1.zip"
        zip_path.write_bytes(r.content)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(DATA_DIR)
        zip_path.unlink()

    cities_path = cities_shp_path()
    if cities_path.exists():
        return
    logger.info("Downloading cities...")
    cities_request = requests.get(CITIES_URL)
    cities_request.raise_for_status()
    zip_path = DATA_DIR / "cities.zip"
    zip_path.write_bytes(cities_request.content)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA_DIR)
    zip_path.unlink()


async def _load_country(database_url: str, country: dict[str, str]) -> None:
    async with create_async_engine(database_url).begin() as conn:
        result = await conn.execute(
            text("""
                INSERT INTO countries (name)
                VALUES (:name)
                ON CONFLICT (name) DO NOTHING
            """),
            {"name": country["name"]},
        )
        logger.info("Country %s upserted %s rows", country["code"], result.rowcount)


async def _load_regions(database_url: str, country: dict[str, str]) -> None:
    geo_data_frame = geopandas.read_file(regions_path(country["code"]))

    ne = geopandas.read_file(regions_shp_path())
    ne_country = ne[ne["admin"] == country["name_en"]][["iso_3166_2", "name_ru"]]

    geo_data_frame = geo_data_frame.merge(
        ne_country,
        left_on="shapeISO",
        right_on="iso_3166_2",
        how="left",
    )

    geo_data_frame["name"] = geo_data_frame["name_ru"].fillna(
        geo_data_frame["shapeName"]
    )
    geo_data_frame["name"] = geo_data_frame["name"].astype(str).str.strip()
    dup_mask = geo_data_frame.duplicated("name", keep="first")
    geo_data_frame["name"] = [
        shape if dup else name
        for name, shape, dup in zip(
            geo_data_frame["name"].values,
            geo_data_frame["shapeName"].values,
            dup_mask.values,
        )
    ]

    geo_data_frame = geo_data_frame[["name", "geometry"]]
    geo_data_frame = geo_data_frame.dropna(subset=["name", "geometry"])
    geo_data_frame = geo_data_frame.set_crs(4326, allow_override=True)
    geo_data_frame = geo_data_frame.rename(columns={"geometry": "border"})
    geo_data_frame = geo_data_frame.set_geometry("border")

    staging = f"regions_staging_{country['code'].lower()}"

    sync_engine = create_engine(to_sync_url(database_url))
    geo_data_frame.to_postgis(
        staging,
        sync_engine,
        if_exists="replace",
        index=False,
        dtype={"border": Geometry("MULTIPOLYGON", srid=4326)},
    )
    sync_engine.dispose()
    async with create_async_engine(database_url).begin() as conn:
        result = await conn.execute(
            text(f"""
                    INSERT INTO regions (name, country_id, border)
                    SELECT rs.name, c.id, rs.border
                    FROM {staging} rs
                    JOIN countries c ON c.name = :country
                    ON CONFLICT (name, country_id) DO UPDATE
                        SET border = EXCLUDED.border
                """),
            {"country": country["name"]},
        )
        await conn.execute(text(f"DROP TABLE {staging}"))
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_regions_border "
                "ON regions USING gist (border)"
            )
        )
    logger.info("Regions upserted for %s (rows: %d)", country["code"], result.rowcount)


async def _load_cities(database_url: str, countries: list[dict[str, str]]) -> None:
    geo_data_frame = geopandas.read_file(cities_shp_path())

    country_names_en = [country["name_en"] for country in countries]
    country_column = next(
        (
            column
            for column in ("SOV0NAME", "SOVEREIGNT", "ADM0NAME", "SOV_A3")
            if column in geo_data_frame.columns
        ),
        None,
    )
    if country_column:
        pattern = "|".join(country_names_en)
        geo_data_frame = geo_data_frame[
            geo_data_frame[country_column]
            .astype(str)
            .str.contains(pattern, case=False, na=False)
        ]

    if "NAME_RU" in geo_data_frame.columns:
        geo_data_frame["name"] = geo_data_frame["NAME_RU"]
    else:
        geo_data_frame = geo_data_frame.rename(columns={"NAME": "name"})
    geo_data_frame["name"] = geo_data_frame["name"].astype(str).str.strip()

    geo_data_frame["coords"] = geo_data_frame.geometry.apply(
        lambda p: f"POINT({p.x} {p.y})" if p else None
    )
    geo_data_frame = geo_data_frame[["name", "coords", "geometry"]]
    geo_data_frame = geo_data_frame.dropna(subset=["name", "coords", "geometry"])
    geo_data_frame = geo_data_frame[geo_data_frame["name"] != "None"]
    geo_data_frame = geo_data_frame.set_crs(4326, allow_override=True)

    sync_engine = create_engine(to_sync_url(database_url))
    geo_data_frame.to_postgis(
        "cities_staging",
        sync_engine,
        if_exists="replace",
        index=False,
        dtype={"coords": Geometry("POINT", srid=4326)},
    )
    sync_engine.dispose()
    async with create_async_engine(database_url).begin() as conn:
        result = await conn.execute(
            text("""
                INSERT INTO cities (name, region_id, coords)
                SELECT name, region_id, coords
                FROM (
                    SELECT DISTINCT ON (cs.name, r.id)
                        cs.name,
                        r.id AS region_id,
                        cs.coords::geography AS coords
                    FROM cities_staging cs
                    JOIN regions r ON ST_Contains(r.border::geometry, cs.coords)
                    ORDER BY cs.name, r.id
                ) AS deduped
                ON CONFLICT (name, region_id) DO UPDATE
                    SET coords = EXCLUDED.coords
            """)
        )
        unmatched_cities = await conn.execute(
            text("""
                SELECT cs.name
                FROM cities_staging cs
                WHERE NOT EXISTS (
                    SELECT 1 FROM regions r
                    WHERE ST_Contains(r.border::geometry, cs.coords)
                )
                ORDER BY cs.name
            """)
        )
        names = [row[0] for row in unmatched_cities]
        await conn.execute(text("DROP TABLE cities_staging"))
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_cities_coords "
                "ON cities USING gist (coords)"
            )
        )
    logger.info(
        "Cities upserted (rows: %s, unmatched: %s)", result.rowcount, unmatched_cities
    )
    if unmatched_cities:
        logger.warning("Unmatched cities (%d): %s", len(names), names)
