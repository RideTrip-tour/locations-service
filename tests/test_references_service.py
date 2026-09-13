import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.db.models import (
    City,
    Country,
    Level,
    LocationLevel,
    LocationStyle,
    Region,
    Style,
)
from app.services.references import ReferenceService

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.crud.references import (
    admin_create_reference,
    admin_delete_reference,
    admin_update_reference,
    list_locations_by_reference,
    list_references,
)
from app.routes.admin import (
    admin_references_router,
    create_cities,
    create_countries,
    create_levels,
    create_regions,
    create_style,
    delete_city_by_id,
    delete_country_by_id,
    delete_level_by_id,
    delete_region_by_id,
    delete_style_by_id,
    read_level_locations,
    read_style_locations,
    update_city_by_id,
    update_country_by_id,
    update_region_by_id,
)
from app.routes.references import (
    read_levels,
    read_styles,
    router,
)
from app.schemas.admin import (
    AdminCityCreate,
    AdminCityUpdate,
    AdminRegionCreate,
    AdminRegionUpdate,
)
from app.schemas.references import ReferenceListResponse
from tests.fakes import FakeSession, make_location, make_reference


def test_list_references_applies_search_and_pagination(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1, name="mountain")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(
        list_references(session, Style, name="mou", limit=10, offset=0)
    )

    assert items == [style]
    assert total == 1


def test_list_references_without_search_returns_all(monkeypatch):
    session = FakeSession()
    level = make_reference(Level, id=2, name="pro")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [level]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Level))

    assert items == [level]
    assert total == 1


def test_list_references_filters_by_single_id(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=5, name="mountain")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Style, id=5))

    assert items == [style]
    assert total == 1


def test_list_references_filters_by_id_list(monkeypatch):
    session = FakeSession()
    styles = [
        make_reference(Style, id=1, name="mountain"),
        make_reference(Style, id=2, name="sea"),
    ]

    async def fake_scalar(statement):
        return 2

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: styles))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Style, id=[1, 2]))

    assert items == styles
    assert total == 2


def test_list_references_filters_by_name(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1, name="mountain")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Style, name="mou"))

    assert items == [style]
    assert total == 1


def test_list_references_combines_name_and_id(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1, name="mountain")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Style, name="mou", id=1))

    assert items == [style]
    assert total == 1


def test_list_references_empty_id_list_returns_all(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1, name="mountain")

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [style]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    items, total = asyncio.run(list_references(session, Style, id=[]))

    assert items == [style]
    assert total == 1


def test_list_references_builds_where_for_name_and_id(monkeypatch):
    session = FakeSession()
    captured = {}

    async def fake_scalar(statement):
        captured["total_sql"] = str(statement.compile(dialect=None))
        return 1

    async def fake_execute(statement):
        captured["sql"] = str(statement.compile(dialect=None))
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    asyncio.run(list_references(session, Style, name="mou", id=[1, 2]))

    sql = captured["sql"]
    assert "styles.id IN" in sql
    assert "lower(styles.name) LIKE" in sql

    total_sql = captured["total_sql"]
    assert "styles.id IN" in total_sql
    assert "lower(styles.name) LIKE" in total_sql


def test_admin_create_reference_commits_and_refreshes(monkeypatch):
    session = FakeSession()

    monkeypatch.setattr(session, "add", lambda obj: None)
    monkeypatch.setattr(session, "commit", session.commit)

    async def fake_refresh(obj, attribute_names=None):
        return None

    monkeypatch.setattr(session, "refresh", fake_refresh)

    result = asyncio.run(admin_create_reference(session, Style, name="mountain"))

    assert result is not None
    assert session.commits == 1


def test_admin_delete_reference_returns_true_when_deleted(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1)

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Style
        assert item_id == 1
        return style

    async def fake_delete(obj):
        return None

    monkeypatch.setattr(
        "app.crud.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(session, "delete", fake_delete)
    monkeypatch.setattr(session, "commit", session.commit)

    result = asyncio.run(admin_delete_reference(session, Style, 1))

    assert result is True
    assert session.commits == 1


def test_admin_delete_reference_returns_false_when_missing(monkeypatch):
    session = FakeSession()

    async def fake_get_reference_by_id(db, model, item_id):
        return None

    monkeypatch.setattr(
        "app.crud.references.get_reference_by_id", fake_get_reference_by_id
    )

    result = asyncio.run(admin_delete_reference(session, Style, 999))

    assert result is False
    assert session.commits == 0


def test_list_locations_by_reference_joins_style_junction(monkeypatch):
    session = FakeSession()
    location = make_location(id=1)

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [location]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    locations, total = asyncio.run(
        list_locations_by_reference(
            session, 1, LocationStyle, LocationStyle.style_id, limit=20, offset=0
        )
    )

    assert locations == [location]
    assert total == 1


def test_list_locations_by_reference_joins_level_junction(monkeypatch):
    session = FakeSession()
    location = make_location(id=1)

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [location]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    locations, total = asyncio.run(
        list_locations_by_reference(
            session, 2, LocationLevel, LocationLevel.level_id, limit=20, offset=0
        )
    )

    assert locations == [location]
    assert total == 1


def test_list_locations_by_reference_filters_by_is_active(monkeypatch):
    session = FakeSession()
    location = make_location(id=1)
    captured = {}

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        captured["sql"] = str(statement.compile(dialect=None))
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [location]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    locations, total = asyncio.run(
        list_locations_by_reference(
            session, 1, LocationStyle, LocationStyle.style_id, is_active=True
        )
    )

    assert locations == [location]
    assert total == 1
    assert "locations.is_active IS true" in captured["sql"]


def test_list_locations_by_reference_without_is_active_returns_all(monkeypatch):
    session = FakeSession()
    location = make_location(id=1)
    captured = {}

    async def fake_scalar(statement):
        return 1

    async def fake_execute(statement):
        captured["sql"] = str(statement.compile(dialect=None))
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [location]))

    monkeypatch.setattr(session, "scalar", fake_scalar)
    monkeypatch.setattr(session, "execute", fake_execute)

    locations, total = asyncio.run(
        list_locations_by_reference(session, 1, LocationStyle, LocationStyle.style_id)
    )

    assert locations == [location]
    assert total == 1
    assert "IS true" not in captured["sql"]


def test_list_styles_returns_reference_list_response(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    style = make_reference(Style, id=1, name="mountain")

    async def fake_list_references(db, model, **kwargs):
        assert db is session
        assert model is Style
        assert kwargs["name"] == "mou"
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 0
        return [style], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_styles(name="mou", limit=10, offset=0))

    assert result.total == 1
    assert result.items[0].name == "mountain"


def test_list_levels_returns_reference_list_response(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    level = make_reference(Level, id=2, name="pro")

    async def fake_list_references(db, model, **kwargs):
        assert db is session
        assert model is Level
        return [level], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_levels())

    assert result.total == 1
    assert result.items[0].name == "pro"


@pytest.mark.asyncio
async def test_create_reference_raises_400_on_duplicate(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_create_reference(db, model, name):
        assert db is session
        assert model is Style
        assert name == "mountain"
        raise IntegrityError("INSERT", None, UniqueViolation())

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_create_style("mountain")

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


def test_create_reference_returns_admin_read(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    style = make_reference(Style, id=1, name="mountain")

    async def fake_admin_create_reference(db, model, name):
        assert db is session
        assert model is Style
        assert name == "mountain"
        return style

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    result = asyncio.run(service.admin_create_style("mountain"))

    assert result.id == 1
    assert result.name == "mountain"


def test_admin_create_country_creates_via_universal_crud(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    country = make_reference(Country, id=1, name="Россия")

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert db is session
        assert model is Country
        assert name == "Россия"
        return country

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    result = asyncio.run(service.admin_create_country("Россия"))

    assert result.id == 1
    assert result.name == "Россия"


def test_admin_create_region_linked_to_country(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    region = make_reference(Region, id=1, name="Краснодарский край")

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Country
        assert item_id == 1
        return make_reference(Country, id=1, name="Россия")

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert db is session
        assert model is Region
        assert name == "Краснодарский край"
        assert kwargs["country_id"] == 1
        return region

    monkeypatch.setattr(
        "app.services.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    result = asyncio.run(
        service.admin_create_region("Краснодарский край", country_id=1)
    )

    assert result.id == 1
    assert result.name == "Краснодарский край"


@pytest.mark.asyncio
async def test_admin_create_region_raises_404_when_country_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert db is session
        assert model is Region
        assert name == "Кубань"
        assert kwargs["country_id"] == 999
        raise IntegrityError("INSERT", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_create_region("Кубань", country_id=999)

    assert exc_info.value.status_code == 404
    assert "Country" in exc_info.value.detail


@pytest.mark.asyncio
async def test_admin_create_region_raises_400_on_duplicate(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert model is Region
        assert kwargs["country_id"] == 1
        raise IntegrityError("INSERT", None, UniqueViolation())

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_create_region("Кубань", country_id=1)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


def test_admin_create_city_linked_to_region(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    city = make_reference(City, id=1, name="Сочи")

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Region
        assert item_id == 1
        return make_reference(Region, id=1, name="Краснодарский край")

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert db is session
        assert model is City
        assert name == "Сочи"
        assert kwargs["region_id"] == 1
        return city

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    result = asyncio.run(service.admin_create_city("Сочи", region_id=1))

    assert result.id == 1
    assert result.name == "Сочи"


@pytest.mark.asyncio
async def test_admin_create_city_raises_404_when_region_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert db is session
        assert model is City
        assert name == "Адлер"
        assert kwargs["region_id"] == 999
        raise IntegrityError("INSERT", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_create_city("Адлер", region_id=999)

    assert exc_info.value.status_code == 404
    assert "Region" in exc_info.value.detail


@pytest.mark.asyncio
async def test_admin_create_city_raises_400_on_duplicate(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_create_reference(db, model, name, **kwargs):
        assert model is City
        assert kwargs["region_id"] == 1
        raise IntegrityError("INSERT", None, UniqueViolation())

    monkeypatch.setattr(
        "app.services.references.admin_create_reference", fake_admin_create_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_create_city("Сочи", region_id=1)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


def test_admin_update_city_with_region_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    city = make_reference(City, id=1, name="Сочи", region_id=1)

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Region
        assert item_id == 2
        return make_reference(Region, id=2, name="Краснодарский край")

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is City
        assert item_id == 1
        assert kwargs["name"] == "Сочи обновлённый"
        assert kwargs["region_id"] == 2
        city.name = kwargs["name"]
        city.region_id = kwargs["region_id"]
        return city

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    result = asyncio.run(
        service.admin_update_city(item_id=1, name="Сочи обновлённый", region_id=2)
    )

    assert result.id == 1
    assert result.name == "Сочи обновлённый"


def test_admin_update_city_without_region_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    city = make_reference(City, id=1, name="Сочи")

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is City
        assert item_id == 1
        assert kwargs == {"name": "Сочи новый"}
        city.name = kwargs["name"]
        return city

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    result = asyncio.run(
        service.admin_update_city(item_id=1, name="Сочи новый", region_id=None)
    )

    assert result.name == "Сочи новый"


def test_admin_update_region_with_country_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    region = make_reference(Region, id=1, name="Краснодарский край", country_id=1)

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Country
        assert item_id == 2
        return make_reference(Country, id=2, name="Россия")

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is Region
        assert item_id == 1
        assert kwargs["name"] == "Краснодарский край обновлённый"
        assert kwargs["country_id"] == 2
        region.name = kwargs["name"]
        region.country_id = kwargs["country_id"]
        return region

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    result = asyncio.run(
        service.admin_update_region(
            item_id=1, name="Краснодарский край обновлённый", country_id=2
        )
    )

    assert result.name == "Краснодарский край обновлённый"


def test_admin_update_region_without_country_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    region = make_reference(Region, id=1, name="Краснодарский край")

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is Region
        assert item_id == 1
        assert kwargs == {"name": "Кубань"}
        region.name = kwargs["name"]
        return region

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    result = asyncio.run(
        service.admin_update_region(item_id=1, name="Кубань", country_id=None)
    )

    assert result.name == "Кубань"


@pytest.mark.asyncio
async def test_admin_update_city_raises_404_when_region_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is City
        assert item_id == 1
        assert kwargs["region_id"] == 999
        raise IntegrityError("UPDATE", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_update_city(item_id=1, name="Сочи", region_id=999)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_admin_update_region_raises_404_when_country_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is Region
        assert item_id == 1
        assert kwargs["country_id"] == 999
        raise IntegrityError("UPDATE", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_update_region(item_id=1, name="Кубань", country_id=999)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


def test_admin_update_reference_commits_and_refreshes(monkeypatch):
    session = FakeSession()
    style = make_reference(Style, id=1, name="old")

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Style
        assert item_id == 1
        return style

    async def fake_refresh(obj, attribute_names=None):
        return None

    monkeypatch.setattr(
        "app.crud.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(session, "commit", session.commit)
    monkeypatch.setattr(session, "refresh", fake_refresh)

    result = asyncio.run(admin_update_reference(session, Style, 1, name="new"))

    assert result is style
    assert style.name == "new"
    assert session.commits == 1


def test_admin_update_reference_returns_none_when_missing(monkeypatch):
    session = FakeSession()

    async def fake_get_reference_by_id(db, model, item_id):
        return None

    monkeypatch.setattr(
        "app.crud.references.get_reference_by_id", fake_get_reference_by_id
    )

    result = asyncio.run(admin_update_reference(session, Style, 999, name="new"))

    assert result is None
    assert session.commits == 0


@pytest.mark.asyncio
async def test_update_reference_raises_404_when_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_get_reference_by_id(db, model, item_id):
        return None

    monkeypatch.setattr(
        "app.crud.references.get_reference_by_id", fake_get_reference_by_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_update_style(item_id=999, name="new")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_reference_raises_400_on_duplicate_name(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is Style
        assert item_id == 1
        assert kwargs == {"name": "new"}
        raise IntegrityError("UPDATE", None, UniqueViolation())

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_update_style(item_id=1, name="new")

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


def test_update_reference_returns_admin_read(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    style = make_reference(Style, id=1, name="new")

    async def fake_get_reference_by_id(db, model, item_id):
        return style

    async def fake_admin_update_reference(db, model, item_id, **kwargs):
        assert db is session
        assert model is Style
        assert item_id == 1
        assert kwargs == {"name": "new"}
        return style

    monkeypatch.setattr(
        "app.services.references.admin_update_reference", fake_admin_update_reference
    )

    result = asyncio.run(service.admin_update_style(item_id=1, name="new"))

    assert result.id == 1
    assert result.name == "new"


@pytest.mark.asyncio
async def test_delete_reference_raises_404_when_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_delete_reference(db, model, item_id):
        return False

    monkeypatch.setattr(
        "app.services.references.admin_delete_reference", fake_admin_delete_reference
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_delete_style(999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_city_raises_409_when_location_linked(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_admin_delete_reference(db, model, item_id):
        assert db is session
        assert model is City
        assert item_id == 1
        raise IntegrityError("statement", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.admin_delete_reference",
        fake_admin_delete_reference,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_delete_city(1)

    assert exc_info.value.status_code == 409
    assert "linked to locations" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_region_raises_409_when_city_linked_to_location(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    region = make_reference(
        Region,
        id=1,
        cities=[make_reference(City, id=1), make_reference(City, id=2)],
    )

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Region
        assert item_id == 1
        return region

    async def fake_admin_delete_reference(db, model, item_id):
        assert db is session
        assert model is Region
        assert item_id == 1
        raise IntegrityError("statement", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(
        "app.services.references.admin_delete_reference",
        fake_admin_delete_reference,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_delete_region(1)

    assert exc_info.value.status_code == 409
    assert "linked to locations" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_country_raises_409_when_city_linked_to_location(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    country = make_reference(
        Country,
        id=1,
        regions=[
            make_reference(
                Region,
                id=1,
                cities=[make_reference(City, id=1)],
            ),
            make_reference(
                Region,
                id=2,
                cities=[make_reference(City, id=2), make_reference(City, id=3)],
            ),
        ],
    )

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Country
        assert item_id == 1
        return country

    async def fake_admin_delete_reference(db, model, item_id):
        assert db is session
        assert model is Country
        assert item_id == 1
        raise IntegrityError("statement", None, ForeignKeyViolation())

    monkeypatch.setattr(
        "app.services.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(
        "app.services.references.admin_delete_reference",
        fake_admin_delete_reference,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.admin_delete_country(1)

    assert exc_info.value.status_code == 409
    assert "linked to locations" in exc_info.value.detail


@pytest.mark.asyncio
async def test_list_reference_locations_raises_404_when_reference_missing(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)

    async def fake_get_reference_by_id(db, model, item_id):
        return None

    monkeypatch.setattr(
        "app.services.references.get_reference_by_id", fake_get_reference_by_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.list_style_locations(999)

    assert exc_info.value.status_code == 404


def test_list_reference_locations_returns_id_name_and_locations(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    style = make_reference(Style, id=1, name="mountain")
    location = make_location(id=1)

    async def fake_get_reference_by_id(db, model, item_id):
        assert db is session
        assert model is Style
        assert item_id == 1
        return style

    async def fake_list_locations_by_reference(
        db, item_id, junction_model, reference_field, **kwargs
    ):
        assert db is session
        assert item_id == 1
        assert junction_model is LocationStyle
        assert reference_field is LocationStyle.style_id
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        assert kwargs["is_active"] is True
        return [location], 1

    monkeypatch.setattr(
        "app.services.references.get_reference_by_id", fake_get_reference_by_id
    )
    monkeypatch.setattr(
        "app.services.references.list_locations_by_reference",
        fake_list_locations_by_reference,
    )

    result = asyncio.run(service.list_style_locations(1, is_active=True))

    assert result.id == 1
    assert result.name == "mountain"
    assert result.total == 1
    assert result.limit == 20
    assert result.offset == 0
    assert result.locations[0].id == 1


def test_read_styles_passes_query_params_to_service():
    service = SimpleNamespace()

    async def fake_list_styles(**kwargs):
        service.kwargs = kwargs
        return SimpleNamespace()

    service.list_styles = fake_list_styles

    asyncio.run(
        read_styles(
            service=service,
            name="mou",
            limit=10,
            offset=5,
        )
    )

    assert service.kwargs["name"] == "mou"
    assert service.kwargs["limit"] == 10
    assert service.kwargs["offset"] == 5


def test_read_levels_passes_query_params_to_service():
    service = SimpleNamespace()

    async def fake_list_levels(**kwargs):
        service.kwargs = kwargs
        return SimpleNamespace()

    service.list_levels = fake_list_levels

    asyncio.run(
        read_levels(
            service=service,
            name="pro",
            limit=10,
            offset=5,
        )
    )

    assert service.kwargs["name"] == "pro"
    assert service.kwargs["limit"] == 10
    assert service.kwargs["offset"] == 5


def test_read_style_locations_passes_params_to_service():
    service = SimpleNamespace()

    async def fake_list_style_locations(style_id, **kwargs):
        service.kwargs = {"style_id": style_id, **kwargs}
        return SimpleNamespace()

    service.list_style_locations = fake_list_style_locations

    asyncio.run(
        read_style_locations(
            style_id=1,
            service=service,
            is_active=True,
            limit=10,
            offset=5,
        )
    )

    assert service.kwargs["style_id"] == 1
    assert service.kwargs["is_active"] is True
    assert service.kwargs["limit"] == 10
    assert service.kwargs["offset"] == 5


def test_read_level_locations_passes_params_to_service():
    service = SimpleNamespace()

    async def fake_list_level_locations(level_id, **kwargs):
        service.kwargs = {"level_id": level_id, **kwargs}
        return SimpleNamespace()

    service.list_level_locations = fake_list_level_locations

    asyncio.run(
        read_level_locations(
            level_id=2,
            service=service,
            is_active=False,
            limit=10,
            offset=5,
        )
    )

    assert service.kwargs["level_id"] == 2
    assert service.kwargs["is_active"] is False
    assert service.kwargs["limit"] == 10
    assert service.kwargs["offset"] == 5


def test_admin_create_style_passes_name_to_service():
    service = SimpleNamespace()

    async def fake_admin_create_style(name):
        service.name = name
        return SimpleNamespace()

    service.admin_create_style = fake_admin_create_style
    style_data = SimpleNamespace(name="mountain")

    asyncio.run(create_style(service=service, style_data=style_data))

    assert service.name == "mountain"


def test_admin_create_levels_passes_name_to_service():
    service = SimpleNamespace()

    async def fake_admin_create_level(name):
        service.name = name
        return SimpleNamespace()

    service.admin_create_level = fake_admin_create_level
    level_data = SimpleNamespace(name="pro")

    asyncio.run(create_levels(service=service, level_data=level_data))

    assert service.name == "pro"


def test_admin_delete_style_passes_id_to_service():
    service = SimpleNamespace()

    async def fake_admin_delete_style(style_id):
        service.style_id = style_id

    service.admin_delete_style = fake_admin_delete_style

    asyncio.run(delete_style_by_id(service=service, style_id=1))

    assert service.style_id == 1


def test_admin_delete_level_passes_id_to_service():
    service = SimpleNamespace()

    async def fake_admin_delete_level(level_id):
        service.level_id = level_id

    service.admin_delete_level = fake_admin_delete_level

    asyncio.run(delete_level_by_id(service=service, level_id=2))

    assert service.level_id == 2


def test_references_openapi_exposes_public_and_admin_paths():
    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_references_router)

    paths = app.openapi()["paths"]

    assert "/api/locations/references/styles" in paths
    assert "/api/locations/references/levels" in paths
    assert "/api/admin/references/styles" in paths
    assert "/api/admin/references/levels" in paths
    assert "/api/admin/references/styles/{style_id}" in paths
    assert "/api/admin/references/levels/{level_id}" in paths
    assert "/api/admin/references/styles/{style_id}/locations" in paths
    assert "/api/admin/references/levels/{level_id}/locations" in paths


def test_references_search_requires_min_three_characters():
    app = FastAPI()
    app.include_router(router)

    parameters = app.openapi()["paths"]["/api/locations/references/styles"]["get"][
        "parameters"
    ]
    search_schema = next(
        parameter["schema"] for parameter in parameters if parameter["name"] == "name"
    )

    assert search_schema["anyOf"][0]["minLength"] == 3


def test_create_countries_passes_name_to_service():
    service = SimpleNamespace()

    async def fake_admin_create_country(name):
        service.name = name
        return SimpleNamespace()

    service.admin_create_country = fake_admin_create_country
    country_data = SimpleNamespace(name="Россия")

    asyncio.run(create_countries(service=service, country_data=country_data))

    assert service.name == "Россия"


def test_create_regions_passes_name_and_country_id():
    service = SimpleNamespace()

    async def fake_admin_create_region(name, country_id):
        service.name = name
        service.country_id = country_id
        return SimpleNamespace()

    service.admin_create_region = fake_admin_create_region
    region_data = SimpleNamespace(name="Краснодарский край", country_id=1)

    asyncio.run(create_regions(service=service, region_data=region_data))

    assert service.name == "Краснодарский край"
    assert service.country_id == 1


def test_create_cities_passes_name_and_region_id():
    service = SimpleNamespace()

    async def fake_admin_create_city(name, region_id):
        service.name = name
        service.region_id = region_id
        return SimpleNamespace()

    service.admin_create_city = fake_admin_create_city
    city_data = SimpleNamespace(name="Сочи", region_id=1)

    asyncio.run(create_cities(service=service, city_data=city_data))

    assert service.name == "Сочи"
    assert service.region_id == 1


def test_update_country_passes_name_to_service():
    service = SimpleNamespace()

    async def fake_admin_update_country(item_id, name):
        service.item_id = item_id
        service.name = name
        return SimpleNamespace()

    service.admin_update_country = fake_admin_update_country
    country_data = SimpleNamespace(name="Россия обновлённая")

    asyncio.run(
        update_country_by_id(service=service, country_id=1, country_data=country_data)
    )

    assert service.item_id == 1
    assert service.name == "Россия обновлённая"


def test_update_region_passes_name_and_country_id():
    service = SimpleNamespace()

    async def fake_admin_update_region(item_id, name, country_id):
        service.item_id = item_id
        service.name = name
        service.country_id = country_id
        return SimpleNamespace()

    service.admin_update_region = fake_admin_update_region
    region_data = SimpleNamespace(name="Кубань", country_id=2)

    asyncio.run(
        update_region_by_id(service=service, region_id=1, region_data=region_data)
    )

    assert service.item_id == 1
    assert service.name == "Кубань"
    assert service.country_id == 2


def test_update_region_passes_country_id_none():
    service = SimpleNamespace()

    async def fake_admin_update_region(item_id, name, country_id):
        service.item_id = item_id
        service.name = name
        service.country_id = country_id
        return SimpleNamespace()

    service.admin_update_region = fake_admin_update_region
    region_data = SimpleNamespace(name="Кубань", country_id=None)

    asyncio.run(
        update_region_by_id(service=service, region_id=1, region_data=region_data)
    )

    assert service.item_id == 1
    assert service.name == "Кубань"
    assert service.country_id is None


def test_update_city_passes_name_and_region_id():
    service = SimpleNamespace()

    async def fake_admin_update_city(item_id, name, region_id):
        service.item_id = item_id
        service.name = name
        service.region_id = region_id
        return SimpleNamespace()

    service.admin_update_city = fake_admin_update_city
    city_data = SimpleNamespace(name="Сочи обновлённый", region_id=2)

    asyncio.run(update_city_by_id(service=service, city_id=1, city_data=city_data))

    assert service.item_id == 1
    assert service.name == "Сочи обновлённый"
    assert service.region_id == 2


def test_update_city_passes_region_id_none():
    service = SimpleNamespace()

    async def fake_admin_update_city(item_id, name, region_id):
        service.item_id = item_id
        service.name = name
        service.region_id = region_id
        return SimpleNamespace()

    service.admin_update_city = fake_admin_update_city
    city_data = SimpleNamespace(name="Сочи обновлённый", region_id=None)

    asyncio.run(update_city_by_id(service=service, city_id=1, city_data=city_data))

    assert service.item_id == 1
    assert service.name == "Сочи обновлённый"
    assert service.region_id is None


def test_delete_country_passes_id_to_service():
    service = SimpleNamespace()

    async def fake_admin_delete_country(country_id):
        service.country_id = country_id

    service.admin_delete_country = fake_admin_delete_country

    asyncio.run(delete_country_by_id(service=service, country_id=1))

    assert service.country_id == 1


def test_delete_region_passes_id_to_service():
    service = SimpleNamespace()

    async def fake_admin_delete_region(region_id):
        service.region_id = region_id

    service.admin_delete_region = fake_admin_delete_region

    asyncio.run(delete_region_by_id(service=service, region_id=2))

    assert service.region_id == 2


def test_delete_city_passes_id_to_service():
    service = SimpleNamespace()

    async def fake_admin_delete_city(city_id):
        service.city_id = city_id

    service.admin_delete_city = fake_admin_delete_city

    asyncio.run(delete_city_by_id(service=service, city_id=3))

    assert service.city_id == 3


def test_admin_references_openapi_exposes_geo_paths():
    app = FastAPI()
    app.include_router(admin_references_router)

    paths = app.openapi()["paths"]

    assert "/api/admin/references/countries" in paths
    assert "/api/admin/references/regions" in paths
    assert "/api/admin/references/cities" in paths
    assert "/api/admin/references/countries/{country_id}" in paths
    assert "/api/admin/references/regions/{region_id}" in paths
    assert "/api/admin/references/cities/{city_id}" in paths


def test_admin_region_create_requires_country_id():
    with pytest.raises(ValidationError):
        AdminRegionCreate(name="Кубань")


def test_admin_city_create_region_id_required():
    with pytest.raises(ValidationError):
        AdminCityCreate(name="Сочи")


def test_admin_region_update_optional_country_id():
    region = AdminRegionUpdate(name="Кубань")
    assert region.country_id is None


def test_admin_city_update_optional_region_id():
    city = AdminCityUpdate(name="Сочи")
    assert city.region_id is None


def test_region_create_schema_requires_country_id_in_openapi():
    app = FastAPI()
    app.include_router(admin_references_router)
    schema = app.openapi()["components"]["schemas"]["AdminRegionCreate"]
    assert "country_id" in schema["required"]


def test_city_create_schema_requires_region_id_in_openapi():
    app = FastAPI()
    app.include_router(admin_references_router)
    schema = app.openapi()["components"]["schemas"]["AdminCityCreate"]
    assert "region_id" in schema["required"]


def test_list_countries_filters_by_name_and_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    country = make_reference(Country, id=1, name="Россия")

    async def fake_list_references(db, model, **kwargs):
        assert db is session
        assert model is Country
        assert kwargs["name"] == "рос"
        assert kwargs["id"] == 1
        return [country], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_countries(name="рос", country_id=1))

    assert result.total == 1
    assert result.items[0].name == "Россия"


def test_list_regions_filters_by_name_and_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    region = make_reference(Region, id=2, name="Краснодарский край")

    async def fake_list_references(db, model, **kwargs):
        assert db is session
        assert model is Region
        assert kwargs["name"] == "крас"
        assert kwargs["id"] == 2
        return [region], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_regions(name="крас", region_id=2))

    assert result.total == 1
    assert result.items[0].name == "Краснодарский край"


def test_list_cities_filters_by_name_and_id(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    city = make_reference(City, id=3, name="Сочи")

    async def fake_list_references(db, model, **kwargs):
        assert db is session
        assert model is City
        assert kwargs["name"] == "сочи"
        assert kwargs["id"] == 3
        return [city], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_cities(name="сочи", city_id=3))

    assert result.total == 1
    assert result.items[0].name == "Сочи"


def test_list_countries_returns_reference_list_response(monkeypatch):
    session = FakeSession()
    service = ReferenceService(session)
    country = make_reference(Country, id=1, name="Россия")

    async def fake_list_references(db, model, **kwargs):
        return [country], 1

    monkeypatch.setattr("app.services.references.list_references", fake_list_references)

    result = asyncio.run(service.list_countries())

    assert isinstance(result, ReferenceListResponse)
    assert result.total == 1
    assert result.items[0].name == "Россия"
