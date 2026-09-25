# Сидер справочников (страны → регионы → города)

Идемпотентный сидер, который загружает справочники стран, регионов и городов
из открытых источников в PostgreSQL + PostGIS.

## Источники данных

| Что | Источник |
|---|---
| Полигоны регионов | [geoBoundaries](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen) (ADM1)
| Русские имена регионов | [Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/) Admin 1
| Города (точки) | [Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-populated-places/) Populated Places

## Что загружается

- **Страны** - из `SUPPORTED_COUNTRIES` в `constants.py`.
- **Регионы** - полигоны из geoBoundaries + русские имена из Natural Earth (merge по ISO-коду).
- **Города** - точки из Natural Earth, привязка к регионам через `ST_DWithin`.
- **Крым и Севастополь** - отдельно из Natural Earth (geoBoundaries их не включает).

## Установка

```
pip install geopandas requests typer
```

## Запуск

```bash
# обычный режим - идемпотентный, если данные есть - пропускает.
python -m scripts.cli seed-geo-data

# только Россия
python -m scripts.cli seed-geo-data --country RU

# Принудительная синхронизация
python -m scripts.cli seed-geo-data --force

# Россия + force
python -m scripts.cli seed-geo-data --country RU --force
```

## Как работает

1. **Проверка PostGIS** - если расширение не установлено, сидер падает с понятной ошибкой.
2. **Проверка идемпотентности** - если все страны из `SUPPORTED_COUNTRIES` есть в БД (с регионами и городами), сидер выходит (`SKIP`).
3. **Скачивание** - файлы скачиваются в `scripts/geo_data/` (временная папка). После успешной загрузки в БД папка **удаляется**.
4. **Загрузка**:
   - `countries` - upsert по `name`.
   - `regions` - upsert по `(name, country_id)`, полигоны из geoBoundaries.
   - `cities` - upsert по `(name, region_id)`, привязка через `ST_DWithin` (допуск ~1 км).
5. **Очистка** - staging-таблицы (`regions_staging_*`, `cities_staging`) удаляются в `finally`.
6. **Кэш** - папка `scripts/geo_data/` удаляется после успешной загрузки.

## Конфигурация

### Добавить страну

В `constants.py` добавить в `SUPPORTED_COUNTRIES` нужную страну:

```python
SUPPORTED_COUNTRIES = [
    {"code": "RU", "name": "Россия", "name_en": "Russia", "gb_open": "RUS"},
    {"code": "KZ", "name": "Казахстан", "name_en": "Kazakhstan", "gb_open": "KAZ"},
]
```

Поля:
- `code` - ISO 3166-1 alpha-2 (для имён файлов).
- `name` - название на русском (как в БД).
- `name_en` - name_en  - название на английском (для фильтра Natural Earth).
- `gb_open` - ISO 3166-1 alpha-3 в верхнем регистре (для geoBoundaries).

Ничего больше менять не надо - сидер сам скачает, загрузит, привяжет.

## Идемпотентность

Сидер можно запускать повторно:
- `ON CONFLICT DO UPDATE` обновляет существующие записи.
- Staging-таблицы удаляются в `finally`.

## Ограничения

- **Крым и Севастополь** - нет в geoBoundaries. Загружаются отдельно из Natural Earth.
- **Не все города** - Natural Earth содержит ~585 значимых городов России из ~1100.
- **Допуск `ST_DWithin`** - ~1 км. Города у границ могут попасть в соседний регион (например, Колпино).
- **Интернет** — нужен при **каждом** запуске (файлы удаляются после успеха).

## Для деплоя

Требования:
- `DATABASE_URL` в окружении.
- `geopandas`, `requests`, `typer` в `requirements.txt`.
- PostGIS установлен в БД **до** запуска сидера (`CREATE EXTENSION postgis`).
- Интернет при первом запуске (или volume на `scripts/geo_data/`).