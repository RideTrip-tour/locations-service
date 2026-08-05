# Location Service

Сервис хранит каталог локаций в отдельной БД и отдаёт API для поиска, фильтрации и избранного.

## API

- `GET /api/locations` - список активных локаций с фильтрами `search`, `region`, `city`, `country`, `activity_id`, `styles`, `levels`, `limit`, `offset`;
- `GET /api/locations/{location_id}` - карточка активной локации;
- `GET /api/locations/filters` - доступные значения фильтров;
- `GET /api/locations/favorites` - активные избранные локации текущего пользователя с теми же фильтрами, что и публичный список;
- `POST /api/locations/{location_id}/favorite` - добавить в избранное;
- `DELETE /api/locations/{location_id}/favorite` - удалить из избранного.

### Admin API

Админские ручки доступны внутри Docker Swarm через gateway. Сервис доверяет заголовкам пользователя, которые устанавливает gateway, и не должен публиковаться наружу напрямую.

- `GET /api/admin/locations/` - список всех локаций, включая неактивные, с фильтрами `search`, `region`, `city`, `country`, `activity_id`, `styles`, `levels`, `limit`, `offset`;
- `GET /api/admin/locations/{location_id}` - карточка локации, включая неактивную;
- `GET /api/admin/locations/filters` - доступные значения фильтров по активным локациям;
- `POST /api/admin/locations/` - создать локацию;
- `DELETE /api/admin/locations/{location_id}` - удалить локацию.

### Фильтры локаций

`region`, `city`, `country`, `styles`, `levels` и `activity_id` принимают одиночное значение, повторяющиеся query-параметры и CSV.

Примеры:

- `GET /api/locations?region=Краснодарский край`
- `GET /api/locations?region=Краснодарский край&region=Карачаево-Черкесия`
- `GET /api/locations?region=Краснодарский край,Карачаево-Черкесия&styles=ski,freeride`
- `GET /api/locations?activity_id=1&activity_id=2`
- `GET /api/locations?activity_id=1,2`

Значения внутри одного поля объединяются через `OR`, разные поля - через `AND`. Например `region=Краснодарский край,Карачаево-Черкесия&styles=ski,freeride` ищет локации в одном из указанных регионов и с одним из указанных стилей. `activity_id` в OpenAPI описан как массив integer, но также поддерживает CSV для удобства клиентов.

`search` применяется как общее ограничение ко всему результату. Публичный API всегда возвращает только активные локации и не принимает `is_active` как query-параметр. Ручка `GET /api/locations/favorites` также возвращает только активные избранные локации.

`location_id` и `activity_id` должны помещаться в диапазон PostgreSQL `integer`: от `1` до `2147483647`. Значения выше этого диапазона возвращают `404 Not Found`, чтобы не передавать некорректный integer в БД.

### Активность локаций

По умолчанию сервисные методы чтения возвращают только локации с `is_active=true`:

- `LocationService.get_location(...)`;
- `LocationService.list_locations(...)`;
- `get_location_by_id(..., only_active=True)`.

Для админских сценариев, где нужны все локации, включая неактивные, используется явное снятие ограничения:

- `LocationService.get_location_for_admin(...)`;
- `LocationService.list_all_locations(...)`;
- `get_location_by_id(..., only_active=False)`.

В избранное можно добавлять только активные локации. Попытка добавить неактивную локацию возвращает `400`.

Локации создаются и удаляются через admin API этого сервиса. Публичные ручки читают каталог и хранят пользовательские избранные.

## Конфигурация

Переменные окружения:

- `DB_LOCATION_SERVICE_HOST`
- `DB_LOCATION_SERVICE_PORT`
- `DB_LOCATION_SERVICE_NAME`
- `DB_LOCATION_SERVICE_USER`
- `DB_LOCATION_SERVICE_PASS`

Для тестовой БД:

- `TEST_DB_LOCATION_SERVICE_NAME`

Entrypoint общий для сервисов и ждёт PostgreSQL и Redis перед запуском API. В Docker Swarm Redis должен быть доступен к моменту старта `location-service`.

Health-check: `GET /api/locations/health`
