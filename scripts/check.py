# scripts/check_region_names.py
"""Проверка совпадения названий регионов между Natural Earth и geoBoundaries."""

import zipfile
from pathlib import Path

import geopandas as gpd
import requests

DATA_DIR = Path("scripts/geo_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEOBOUNDARIES_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
    "releaseData/gbOpen/RUS/ADM1/geoBoundaries-RUS-ADM1.geojson"
)
CITIES_URL = (
    "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places.zip"
)


def download(url: str, path: Path) -> Path:
    if path.exists():
        return path
    print(f"Downloading {path.name}...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def main() -> None:
    # 1. Регионы из geoBoundaries
    regions_path = download(GEOBOUNDARIES_URL, DATA_DIR / "regions_ru.geojson")
    regions = gpd.read_file(regions_path)

    print("=" * 70)
    print("geoBoundaries columns:", regions.columns.tolist())
    print("=" * 70)

    # Ищем колонку с именем
    region_name_col = None
    for col in ("shapeName", "NAME", "name"):
        if col in regions.columns:
            region_name_col = col
            break

    if region_name_col is None:
        print("❌ Не нашла колонку с именем региона в geoBoundaries")
        print("Доступные колонки:", regions.columns.tolist())
        return

    gb_names = set(regions[region_name_col].astype(str).str.strip())
    print(f"\ngeoBoundaries: {len(gb_names)} регионов")
    print(f"Использую колонку: {region_name_col}")
    print("Примеры:")
    for name in list(gb_names)[:10]:
        print(f"  - {name}")

    # 2. Города из Natural Earth
    cities_zip = download(CITIES_URL, DATA_DIR / "cities.zip")

    # Распакуем, если ещё не
    shp = DATA_DIR / "ne_10m_populated_places.shp"
    if not shp.exists():
        with zipfile.ZipFile(cities_zip) as z:
            z.extractall(DATA_DIR)

    cities = gpd.read_file(shp)

    print("\n" + "=" * 70)
    print("Natural Earth columns (первые 30):", cities.columns.tolist()[:30])
    print("=" * 70)

    # Фильтр по России
    country_col = next(
        (c for c in ("SOVEREIGNT", "ADM0NAME", "SOV_A3") if c in cities.columns),
        None,
    )
    if country_col:
        cities_ru = cities[
            cities[country_col].astype(str).str.contains("Russia", case=False, na=False)
        ]
    else:
        cities_ru = cities

    print(f"\nГородов России в Natural Earth: {len(cities_ru)}")

    # Колонка с регионом
    adm1_col = next(
        (c for c in ("ADM1NAME", "adm1name", "ADM1_NAME") if c in cities_ru.columns),
        None,
    )
    if adm1_col is None:
        print("❌ Не нашла колонку ADM1NAME")
        print("Доступные колонки:", cities_ru.columns.tolist())
        return

    ne_names = set(cities_ru[adm1_col].dropna().astype(str).str.strip())
    ne_names.discard("")
    ne_names.discard("nan")

    print(f"Уникальных регионов в ADM1NAME: {len(ne_names)}")
    print("Примеры:")
    for name in list(ne_names)[:15]:
        print(f"  - {name}")

    # 3. Сравнение
    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ")
    print("=" * 70)

    matched = ne_names & gb_names
    only_ne = ne_names - gb_names
    only_gb = gb_names - ne_names

    print(f"\n✅ Совпадают: {len(matched)}")
    for name in sorted(matched)[:20]:
        print(f"  - {name}")

    print(f"\n⚠️  Только в Natural Earth ({len(only_ne)}):")
    for name in sorted(only_ne)[:20]:
        print(f"  - {name}")

    print(f"\n⚠️  Только в geoBoundaries ({len(only_gb)}):")
    for name in sorted(only_gb)[:20]:
        print(f"  - {name}")

    # Итог
    print("\n" + "=" * 70)
    total = len(ne_names | gb_names)
    if total:
        pct = len(matched) / total * 100
        print(f"Совпадение: {len(matched)}/{total} ({pct:.1f}%)")
    print("=" * 70)

    # Какой процент городов найдёт свой регион
    if adm1_col in cities_ru.columns:
        cities_ru_valid = cities_ru[cities_ru[adm1_col].notna()]
        cities_with_match = cities_ru_valid[
            cities_ru_valid[adm1_col].astype(str).str.strip().isin(gb_names)
        ]
        pct_cities = (
            len(cities_with_match) / len(cities_ru_valid) * 100
            if len(cities_ru_valid)
            else 0
        )
        print(
            f"\nГородов, которые найдут регион: "
            f"{len(cities_with_match)}/{len(cities_ru_valid)} ({pct_cities:.1f}%)"
        )
    regions = gpd.read_file("scripts/geo_data/regions_ru.geojson")
    print(regions["shapeName"].tolist())


if __name__ == "__main__":
    main()
