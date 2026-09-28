"""A stand-in for the Workers D1 binding, backed by Cloudflare's D1 HTTP
query API instead -- for running src/sync.py from a GitHub Actions runner
(scripts/run_sync.py) rather than inside the deployed Worker. src/db.py's
query()/query_one()/execute()/batch() helpers only ever call
env.DB.prepare(sql).bind(*params).all()/.first()/.run() and
env.DB.batch([...]) -- they never touch the Workers binding directly -- so
matching that same shape here means sync.py and db.py need zero changes to
run in either place.

https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database
"""

import json
import urllib.error
import urllib.request


class D1HttpError(Exception):
    """A Cloudflare D1 HTTP API call failed, or returned success: false."""


def _post(url, api_token, body):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer {}".format(api_token),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise D1HttpError(
            "{} responded {}: {}".format(url, error.code, error.read().decode("utf-8", "replace"))
        )
    except urllib.error.URLError as error:
        raise D1HttpError("{} unreachable: {}".format(url, error))
    if not payload.get("success"):
        raise D1HttpError("{} returned errors: {}".format(url, payload.get("errors")))
    return payload["result"]


class _RunResult:
    """Shaped like a real D1Result -- db.py's execute()/batch() only ever
    read .meta.changes off of this."""

    def __init__(self, changes):
        self.meta = _Meta(changes)


class _Meta:
    def __init__(self, changes):
        self.changes = changes


class _AllResult:
    """Shaped like a real D1Result -- db.py's query() only ever reads
    .results off of this."""

    def __init__(self, results):
        self.results = results


class _Statement:
    def __init__(self, binding, sql, params=()):
        self._binding = binding
        self._sql = sql
        self._params = tuple(params)

    def bind(self, *params):
        return _Statement(self._binding, self._sql, params)

    async def all(self):
        return _AllResult(self._binding._run_one(self._sql, self._params).get("results") or [])

    async def first(self):
        rows = self._binding._run_one(self._sql, self._params).get("results") or []
        return rows[0] if rows else None

    async def run(self):
        meta = self._binding._run_one(self._sql, self._params).get("meta") or {}
        return _RunResult(meta.get("changes", 0) or 0)


class LiveD1:
    """Cloudflare's D1 HTTP query API, shaped like the Workers D1 binding
    src/db.py already targets."""

    def __init__(self, account_id, database_id, api_token):
        self._url = "https://api.cloudflare.com/client/v4/accounts/{}/d1/database/{}/query".format(
            account_id, database_id
        )
        self._api_token = api_token

    def prepare(self, sql):
        return _Statement(self, sql)

    def _run_one(self, sql, params):
        result = _post(self._url, self._api_token, {"sql": sql, "params": list(params)})
        return result[0] if result else {}

    async def batch(self, statements):
        """Run every statement as one D1 API call -- the same atomicity
        env.DB.batch() gives inside a Worker (see sync._create_fixture_from_sync,
        which reads groups.total_seats live inside the same transaction its
        own seat-count insert runs in, specifically to avoid a resize race).

        The request body is a JSON *array* of {"sql", "params"} objects, one
        per statement, each with its own independently-bound params -- not
        one combined SQL string with a single flattened params array. An
        earlier version of this method built exactly that combined form
        (statements' SQL joined by ';', their params concatenated into one
        list) on the assumption that the HTTP query API's only
        multi-statement input was one semicolon-joined body sharing a single
        params array; that was wrong, and broke every fixture-creation sync
        run with a real 400 from Cloudflare: "The request is malformed:
        params with multiple statements is not supported". The API does
        execute multiple statements atomically in one call, but only when
        each one is a separate object in the request body, each carrying
        its own params -- see
        https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database
        (the "Send multiple queries" batch form)."""
        if not statements:
            return []
        body = [{"sql": statement._sql, "params": list(statement._params)} for statement in statements]
        result = _post(self._url, self._api_token, body)
        return [_RunResult((entry.get("meta") or {}).get("changes", 0) or 0) for entry in result]
