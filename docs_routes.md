# Документация API `locations-service` (роуты)

Ниже — актуальная документация по HTTP-роутам микросервиса локаций.

## Общие правила

- Базовый префикс всех роутов: `/locations`.
- Формат данных: `application/json`.
- Для пользовательских операций используется заголовок `x-user-id` (передаётся API Gateway).
- Если `x-user-id` не передан для защищённого роута — ответ `401 Authentication required`.

---

## 1) Сервисные роуты

### `GET /locations/health`
Проверка доступности сервиса.

**Ответ 200**
```json
{
  "status": "ok",
  "service": "locations-service"
}
```

---

## 2) Поиск и выдача локаций

### `GET /locations/search`
Расширенный поиск локаций для списка/каталога.

**Query-параметры**
- `q` (string) — текстовый поиск по `name/display_name/description`.
- `region_id` (int) — фильтр по региону.
- `city_id` (int) — фильтр по городу.
- `level_id` (int) — фильтр по уровню.
- `activity_id` (int) — фильтр по активности.
- `latitude` (float), `longitude` (float), `radius_km` (float) — геофильтр в радиусе.
- `season_month` (int, 1..12) — фильтр по сезонности.
- `has_airport` (bool), `has_railway_station` (bool), `has_bus_station` (bool) — инфраструктурные фильтры.
- `page` (int, default `1`) — номер страницы.
- `page_size` (int, default `20`, max `100`) — размер страницы.
- `view` (`list|map`, default `list`) — режим выдачи.

**Ответ 200**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Arkhyz",
      "display_name": "Архыз",
      "location_type": "resort",
      "region": "Карачаево-Черкесия",
      "city": "Минеральные Воды",
      "latitude": 43.56,
      "longitude": 41.28,
      "description": "...",
      "is_favorite": true,
      "compatibility_status": "unknown",
      "compatibility_reason": null,
      "distance_from_city_km": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "view": "list"
}
```

---

### `GET /locations/map`
Компактная выдача для карты (map pins), по сути `search` в режиме `view=map`.

**Query-параметры**
- `region_id` (int)
- `city_id` (int)
- `activity_id` (int)

**Ответ 200**
Формат такой же, как у `/locations/search`, но поле `view` = `"map"`.

---

## 3) Справочники фильтров

### `GET /locations/regions`
Получить список регионов.

**Ответ 200**
```json
[{"id": 1, "name": "Алтай"}]
```

### `GET /locations/cities?region_id=...`
Получить города, опционально по региону.

**Ответ 200**
```json
[{"id": 10, "region_id": 1, "name": "Горно-Алтайск"}]
```

### `GET /locations/activities`
Список активностей.

**Ответ 200**
```json
[{"id": 1, "code": "skiing", "name": "Горные лыжи"}]
```

### `GET /locations/levels`
Список уровней.

**Ответ 200**
```json
[{"id": 1, "code": "beginner", "name": "Начинающий"}]
```

---

## 4) Избранное (требует `x-user-id`)

### `POST /locations/{location_id}/favorite`
Добавить локацию в избранное.

**Ответ 200**
```json
{"location_id": 12, "is_favorite": true}
```

### `DELETE /locations/{location_id}/favorite`
Удалить локацию из избранного.

**Ответ 200**
```json
{"location_id": 12, "is_favorite": false}
```

### `GET /locations/favorites`
Получить список избранных локаций пользователя.

**Ответ 200**
Массив объектов `LocationResponse`.

---

## 5) Совместимость локации

### `POST /locations/{location_id}/compatibility-check`
Проверка совместимости локации с параметрами поездки.

**Тело запроса**
```json
{
  "date_from": "2026-07-10",
  "date_to": "2026-07-17",
  "activity_id": 1,
  "level_id": 2,
  "style": "sport",
  "duration_days": 7,
  "budget": 120000,
  "transport": "air"
}
```

**Ответ 200**
```json
{
  "location_id": 12,
  "status": "compatible",
  "reason": null
}
```

**Ответ 404**
```json
{"detail": "Location not found"}
```

---

## 6) Сохранение выбора локации в конфигуратор (требует `x-user-id`)

### `POST /locations/trip-configs/{config_id}/location`
Сохраняет выбранную локацию для черновика/конфига поездки.

**Тело запроса**
```json
{"location_id": 12}
```

**Ответ 200**
```json
{
  "config_id": 101,
  "location_id": 12,
  "saved_at": "2026-04-19T10:00:00Z"
}
```

---

## 7) Базовые CRUD-роуты локаций

### `GET /locations/`
Список локаций (`skip`, `limit`).

### `GET /locations/{location_id}`
Получение одной локации по ID.

**Ошибки**
- `404 Location not found`

---

## Рекомендации по интеграции в микросервисной архитектуре

1. `x-user-id` должен проксироваться только доверенным gateway.
2. Для `/search` с большим каталогом рекомендуется включить кэш и ограничения `page_size`.
3. Для `/map` на фронтенде обычно нужен debounce + bbox/radius фильтрация.
4. Для межсервисной синхронизации `trip-config` лучше использовать событие (outbox/event bus), если запись хранится в отдельном сервисе.
