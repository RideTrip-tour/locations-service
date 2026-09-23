from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "geo_data"


#   code     — ISO 3166-1 alpha-2 (для имён файлов и флагов CLI)
#   name     — название на русском (как в БД, таблица countries.name)
#   name_en  — название на английском (для фильтра Natural Earth)
#   gb_open  — ISO 3166-1 alpha-3 в верхнем регистре (для geoBoundaries)

SUPPORTED_COUNTRIES: list[dict[str, str]] = [
    {"code": "RU", "name": "Россия", "name_en": "Russia", "gb_open": "RUS"},
]

REGIONS_ADM1_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/{gb_open}/ADM1/geoBoundaries-{gb_open}-ADM1.geojson"

CITIES_URL = (
    "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places.zip"
)


def regions_path(code: str) -> Path:
    """Путь к GeoJSON с регионами конкретной страны."""
    return DATA_DIR / f"regions_{code.lower()}.geojson"


def cities_shp_path() -> Path:
    """Путь к Shapefile с городами (общий для всех стран)."""
    return DATA_DIR / "ne_10m_populated_places.shp"


def to_sync_url(async_url: str) -> str:
    """postgresql+asyncpg://... → postgresql+psycopg2://..."""
    return async_url.replace("+asyncpg", "+psycopg2")
