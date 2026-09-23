"""Shared fakes and factories for service tests."""

from types import SimpleNamespace


class FakeSession:
    """Minimal async session stub. Each method raises unless monkeypatched."""

    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, statement):
        raise AssertionError("FakeSession.execute should be monkeypatched")

    async def scalar(self, statement):
        raise AssertionError("FakeSession.scalar should be monkeypatched")

    def add(self, obj):
        raise AssertionError("FakeSession.add should be monkeypatched")

    async def refresh(self, obj, attribute_names=None):
        raise AssertionError("FakeSession.refresh should be monkeypatched")

    async def delete(self, obj):
        raise AssertionError("FakeSession.delete should be monkeypatched")


class DictLikeNamespace(SimpleNamespace):
    """SimpleNamespace with dict-like access."""

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)


class FakeSeries:
    def __init__(self, values):
        self.values = list(values)

    def __eq__(self, other):
        return FakeSeries([v == other for v in self.values])

    def __ne__(self, other):
        return FakeSeries([v != other for v in self.values])

    def astype(self, _):
        return self

    def apply(self, func):
        return FakeSeries([func(v) for v in self.values])

    @property
    def str(self):
        return self

    def strip(self):
        return FakeSeries([v.strip() if isinstance(v, str) else v for v in self.values])

    def contains(self, pattern, case=False, na=False):
        variants = [p.lower() for p in pattern.split("|")]
        return FakeSeries(
            [any(v in str(val).lower() for v in variants) for val in self.values]
        )

    def fillna(self, other):
        fallback = (
            other.values
            if isinstance(other, FakeSeries)
            else [other] * len(self.values)
        )
        return FakeSeries(
            [fallback[i] if v is None else v for i, v in enumerate(self.values)]
        )


class FakeGeoDataFrame:
    def __init__(self, rows):
        self.rows = [dict(r) for r in rows]

    @property
    def columns(self):
        return list(self.rows[0].keys()) if self.rows else []

    def __getitem__(self, key):
        if isinstance(key, str):
            return FakeSeries([r.get(key) for r in self.rows])
        if isinstance(key, list):
            return FakeGeoDataFrame([{k: r.get(k) for k in key} for r in self.rows])
        return FakeGeoDataFrame([r for r, flag in zip(self.rows, key.values) if flag])

    def __setitem__(self, key, value):
        for i, r in enumerate(self.rows):
            r[key] = value.values[i] if isinstance(value, FakeSeries) else value

    def merge(self, right, left_on, right_on, how):
        by_key = {r.get(right_on): r for r in right.rows}
        merged = []
        for row in self.rows:
            combined = dict(row)
            combined.update(
                {
                    k: v
                    for k, v in by_key.get(row.get(left_on), {}).items()
                    if k not in combined
                }
            )
            merged.append(combined)
        return FakeGeoDataFrame(merged)

    def duplicated(self, column, keep="first"):
        seen = set()
        mask = []
        for r in self.rows:
            v = r.get(column)
            mask.append(v in seen)
            seen.add(v)
        return FakeSeries(mask)

    def dropna(self, subset=None):
        keys = subset or self.columns
        return FakeGeoDataFrame(
            [r for r in self.rows if all(r.get(k) is not None for k in keys)]
        )

    def set_crs(self, *args, **kwargs):
        return self

    def rename(self, columns):
        return FakeGeoDataFrame(
            [{columns.get(k, k): v for k, v in r.items()} for r in self.rows]
        )

    def set_geometry(self, column):
        return self

    @property
    def geometry(self):
        return FakeSeries([r.get("geometry") for r in self.rows])

    def to_postgis(self, table, engine, **kwargs):
        if not hasattr(self, "_to_postgis_calls"):
            self._to_postgis_calls = []
        self._to_postgis_calls.append(
            {
                "table": table,
                "engine": engine,
                "if_exists": kwargs.get("if_exists"),
                "index": kwargs.get("index"),
                "dtype": kwargs.get("dtype"),
                "rows": self.rows,
            }
        )


class FakeResult:
    def __init__(self, rowcount=0, rows=()):
        self.rowcount = rowcount
        self._rows = list(rows)

    def __iter__(self):
        return iter(self._rows)


class FakeAsyncConn:
    """async-connection fake."""

    def __init__(self, log=None, scalars=None, rows=(), rowcount=1):
        self.log = log if log is not None else []
        self.rowcount = rowcount
        self._scalars = list(scalars or [])
        self._i = 0
        self._rows = list(rows)

    async def execute(self, statement, params=None):
        self.log.append(("execute", str(statement), params))
        return FakeResult(rowcount=self.rowcount, rows=self._rows)

    async def scalar(self, statement, params=None):
        self.log.append(("scalar", str(statement), params))
        if self._i < len(self._scalars):
            v = self._scalars[self._i]
            self._i += 1
            return v
        return None


class FakeBegin:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        return False


class FakeAsyncEngine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return FakeBegin(self.conn)


class FakeSyncEngine:
    def __init__(self, log=None):
        self.log = log if log is not None else []
        self.disposed = False

    def dispose(self):
        self.disposed = True


def make_reference(model, **overrides):
    """Build a reference-like object (Style/Level) with id and name."""
    payload = {"id": 1, "name": "новичок"}
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_location(**overrides):
    """Build a location-like object with all fields used by LocationRead."""
    country = overrides.pop("country", SimpleNamespace(name="Russia"))
    region = overrides.pop(
        "region", SimpleNamespace(name="Краснодарский край", country=country)
    )
    city_rel = overrides.pop(
        "city_rel", SimpleNamespace(name="Сочи", region=region, country=country)
    )
    payload = {
        "id": 1,
        "slug": "rosa-khutor",
        "name": "Роза Хутор",
        "city_id": 1,
        "city": "Сочи",
        "region": "Краснодарский край",
        "country": "Russia",
        "city_rel": city_rel,
        "description": None,
        "latitude": 43.674,
        "longitude": 40.206,
        "distance_to_city_km": 70,
        "activity_ids": [12],
        "styles": ["mountain"],
        "levels": ["beginner"],
        "is_active": True,
        "created_at": "2026-04-13T00:00:00Z",
        "updated_at": "2026-04-13T00:00:00Z",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_country(**overrides) -> DictLikeNamespace:
    """Country for seeder."""
    payload = {"code": "RU", "name": "Россия", "name_en": "Russia", "gb_open": "RUS"}
    payload.update(overrides)
    return DictLikeNamespace(**payload)
