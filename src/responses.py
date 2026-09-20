"""Request and response helpers for the Worker runtime.

Named responses.py rather than http.py so it cannot shadow the standard
library's http package inside the runtime."""

import json

from js import Object, Response
from pyodide.ffi import to_js

JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}


class ApiError(Exception):
    """Raised by handlers to return a specific status without unwinding."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _to_js_options(status, headers):
    merged = dict(JSON_HEADERS)
    merged.update(headers or {})
    return to_js(
        {"status": status, "headers": merged},
        dict_converter=Object.fromEntries,
    )


def json_response(data, status=200, headers=None):
    return Response.new(json.dumps(data), _to_js_options(status, headers))


def error_response(status, message):
    return json_response({"error": message}, status=status)


def no_content():
    return Response.new(None, _to_js_options(204, {}))


async def read_json(request):
    """Parse a JSON request body, or raise ApiError(400)."""
    try:
        body = await request.text()
    except Exception:
        raise ApiError(400, "Could not read the request body")
    if not body:
        raise ApiError(400, "Expected a JSON body")
    try:
        parsed = json.loads(body)
    except ValueError:
        raise ApiError(400, "Request body is not valid JSON")
    if not isinstance(parsed, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return parsed


def require(body, *fields):
    """Pull required fields out of a parsed body, or raise ApiError(400)."""
    missing = [field for field in fields if body.get(field) in (None, "")]
    if missing:
        raise ApiError(400, "Missing required field(s): " + ", ".join(missing))
    return [body[field] for field in fields]
