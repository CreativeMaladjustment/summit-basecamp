"""Stand-ins for the Workers runtime, so handlers can be tested off-platform.

`wrangler dev` needs to download the Pyodide runtime, which is not always
reachable. These fakes give the same surface the Worker code uses -- a D1
binding over an in-memory SQLite database, a KV binding, and the `js` and
`pyodide` modules `responses.py` imports -- so the routing, SQL and handler
logic can be exercised with plain CPython.
"""

import json
import sqlite3
import sys
import types


# --- the `js` and `pyodide` modules the Worker code imports ----------------


class FakeHeaders:
    def __init__(self, initial=None):
        self._values = dict(initial or {})

    def get(self, name):
        for key, value in self._values.items():
            if key.lower() == name.lower():
                return value
        return None

    def set(self, name, value):
        self._values[name] = value

    def to_dict(self):
        return dict(self._values)


class FakeResponse:
    def __init__(self, body, options=None):
        options = options or {}
        self.body = body
        self.status = options.get("status", 200)
        self.headers = FakeHeaders(options.get("headers"))

    @classmethod
    def new(cls, body, options=None):
        return cls(body, options)

    def json(self):
        return json.loads(self.body)


class FakeURL:
    def __init__(self, url):
        self.pathname = url.split("?", 1)[0].split("#", 1)[0]
        for prefix in ("http://", "https://"):
            if self.pathname.startswith(prefix):
                rest = self.pathname[len(prefix) :]
                slash = rest.find("/")
                self.pathname = rest[slash:] if slash != -1 else "/"
                break

    @classmethod
    def new(cls, url):
        return cls(url)


def install_runtime_stubs():
    """Register fake `js` and `pyodide` modules, before importing Worker code."""
    js = types.ModuleType("js")
    js.Response = FakeResponse
    js.URL = FakeURL
    js.Object = types.SimpleNamespace(fromEntries=lambda pairs: pairs)
    sys.modules["js"] = js

    pyodide = types.ModuleType("pyodide")
    ffi = types.ModuleType("pyodide.ffi")
    # The real to_js converts a dict to a JS object; here it stays a dict,
    # which is what FakeResponse expects.
    ffi.to_js = lambda value, dict_converter=None, **kwargs: value
    pyodide.ffi = ffi
    sys.modules["pyodide"] = pyodide
    sys.modules["pyodide.ffi"] = ffi


# --- bindings --------------------------------------------------------------


class FakeStatement:
    def __init__(self, connection, sql, params=()):
        self._connection = connection
        self._sql = sql
        self._params = tuple(params)

    def bind(self, *params):
        return FakeStatement(self._connection, self._sql, params)

    async def all(self):
        cursor = self._connection.execute(self._sql, self._params)
        rows = [dict(row) for row in cursor.fetchall()]
        return types.SimpleNamespace(results=rows, success=True)

    async def first(self):
        cursor = self._connection.execute(self._sql, self._params)
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    async def run(self):
        cursor = self._connection.execute(self._sql, self._params)
        self._connection.commit()
        return types.SimpleNamespace(
            meta=types.SimpleNamespace(changes=cursor.rowcount if cursor.rowcount > 0 else 0)
        )


class FakeD1:
    def __init__(self, connection):
        self._connection = connection

    def prepare(self, sql):
        return FakeStatement(self._connection, sql)

    async def batch(self, statements):
        results = []
        for statement in statements:
            results.append(await statement.run())
        return results


class FakeKV:
    def __init__(self, values=None):
        self._values = dict(values or {})

    async def get(self, key):
        return self._values.get(key)

    async def put(self, key, value):
        self._values[key] = value


class FakeRequest:
    def __init__(self, method="GET", url="http://localhost/", headers=None, body=None):
        self.method = method
        self.url = url
        self.headers = FakeHeaders(headers)
        self._body = body

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)


def make_env(schema_path, seed_path=None, environment="development"):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    with open(schema_path) as handle:
        connection.executescript(handle.read())
    if seed_path:
        with open(seed_path) as handle:
            connection.executescript(handle.read())
    connection.commit()
    return types.SimpleNamespace(
        DB=FakeD1(connection),
        SESSIONS=FakeKV(),
        ENVIRONMENT=environment,
    )
