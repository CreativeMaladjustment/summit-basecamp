"""Real js/pyodide stand-ins, so src/sync_sources.py's `from js import
fetch` (and the pyodide.ffi.to_js call inside its _js_options helper) can
run under plain CPython on a GitHub Actions runner instead of inside the
Workers/Pyodide runtime.

Mirrors tests/fake_workers.py's install_runtime_stubs() exactly -- same
module shapes, same passthrough to_js -- except js.fetch here makes a real
network request instead of returning a canned response. Must be imported
and have install() called before sync_sources/sync are imported anywhere
in the process, since `from js import fetch` binds that name once, at
first import.
"""

import asyncio
import json
import sys
import types
import urllib.error
import urllib.request


class LiveFetchResponse:
    def __init__(self, status, body):
        self.status = status
        self.ok = 200 <= status < 300
        self._body = body

    async def text(self):
        return self._body

    async def json(self):
        return json.loads(self._body)


def _blocking_request(url, method, headers):
    request = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        # sync_sources._get_text only checks response.ok/response.status --
        # a non-2xx is a normal response to it, not a raised exception, the
        # same way a real Workers fetch() never raises for one either.
        return error.code, error.read().decode("utf-8", "replace")


async def _live_fetch(url, options=None):
    options = options or {}
    method = options.get("method", "GET")
    headers = dict(options.get("headers") or {})
    status, body = await asyncio.to_thread(_blocking_request, url, method, headers)
    return LiveFetchResponse(status, body)


def install():
    js = types.ModuleType("js")
    js.fetch = _live_fetch
    # Real Object.fromEntries turns a list of [k, v] pairs into a dict --
    # never actually exercised here since to_js below is a passthrough that
    # never calls its dict_converter, same as fake_workers.py's own stub.
    js.Object = types.SimpleNamespace(fromEntries=dict)
    sys.modules["js"] = js

    pyodide = types.ModuleType("pyodide")
    ffi = types.ModuleType("pyodide.ffi")
    ffi.to_js = lambda value, dict_converter=None, **kwargs: value
    pyodide.ffi = ffi
    sys.modules["pyodide"] = pyodide
    sys.modules["pyodide.ffi"] = ffi
