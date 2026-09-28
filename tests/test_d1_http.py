"""Unit tests for scripts/d1_http.py -- the Cloudflare D1 HTTP API stand-in
for the Workers D1 binding, used to run src/sync.py from GitHub Actions
(scripts/run_sync.py). urllib.request.urlopen is monkeypatched so these
never touch the real network or a real Cloudflare account.
"""

import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from d1_http import D1HttpError, LiveD1  # noqa: E402


class FakeUrlopenContext:
    """A context manager matching what `with urllib.request.urlopen(...) as
    response:` needs -- .status/.read(), entered/exited like a real one."""

    def __init__(self, status, body):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


class D1HttpTests(unittest.TestCase):
    def setUp(self):
        self.captured_requests = []

    def _install_response(self, status, payload):
        body = json.dumps(payload).encode("utf-8")

        def fake_urlopen(request, timeout=None):
            self.captured_requests.append(request)
            if status >= 400:
                raise urllib.error.HTTPError(request.full_url, status, "error", {}, mock.MagicMock(read=lambda: body))
            return FakeUrlopenContext(status, body)

        patcher = mock.patch("urllib.request.urlopen", side_effect=fake_urlopen)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_all_returns_rows_from_the_first_result_entry(self):
        self._install_response(200, {"success": True, "result": [{"results": [{"id": "grp_1"}]}]})
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        result = asyncio.run(db.prepare("SELECT * FROM groups").all())

        self.assertEqual(result.results, [{"id": "grp_1"}])

    def test_first_returns_none_when_no_rows(self):
        self._install_response(200, {"success": True, "result": [{"results": []}]})
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        row = asyncio.run(db.prepare("SELECT * FROM groups WHERE id = ?").bind("nope").first())

        self.assertIsNone(row)

    def test_run_returns_changes_from_meta(self):
        self._install_response(200, {"success": True, "result": [{"meta": {"changes": 3}}]})
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        result = asyncio.run(db.prepare("UPDATE groups SET name = ?").bind("New Name").run())

        self.assertEqual(result.meta.changes, 3)

    def test_request_carries_the_bearer_token_and_sql_plus_params(self):
        self._install_response(200, {"success": True, "result": [{"results": []}]})
        db = LiveD1("acct_1", "db_1", "tok_secret")

        import asyncio

        asyncio.run(db.prepare("SELECT * FROM groups WHERE id = ?").bind("grp_1").all())

        request = self.captured_requests[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer tok_secret")
        self.assertIn("/accounts/acct_1/d1/database/db_1/query", request.full_url)
        body = json.loads(request.data)
        self.assertEqual(body["sql"], "SELECT * FROM groups WHERE id = ?")
        self.assertEqual(body["params"], ["grp_1"])

    def test_an_http_error_raises_d1_http_error_with_the_body(self):
        self._install_response(403, {"success": False, "errors": [{"message": "not authorized"}]})
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        with self.assertRaises(D1HttpError) as cm:
            asyncio.run(db.prepare("SELECT 1").all())
        self.assertIn("403", str(cm.exception))

    def test_success_false_raises_d1_http_error(self):
        self._install_response(200, {"success": False, "errors": [{"message": "bad sql"}]})
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        with self.assertRaises(D1HttpError) as cm:
            asyncio.run(db.prepare("NOT VALID SQL").all())
        self.assertIn("bad sql", str(cm.exception))

    def test_batch_joins_statements_and_flattens_params_in_order(self):
        self._install_response(200, {
            "success": True,
            "result": [{"meta": {"changes": 1}}, {"meta": {"changes": 4}}],
        })
        db = LiveD1("acct_1", "db_1", "tok_1")
        statements = [
            db.prepare("INSERT INTO fixtures (id, opponent) VALUES (?, ?)").bind("fix_1", "Reign"),
            db.prepare("INSERT INTO seat_allocations (fixture_id, seat_number) VALUES (?, ?)").bind("fix_1", 1),
        ]

        import asyncio

        results = asyncio.run(db.batch(statements))

        self.assertEqual([r.meta.changes for r in results], [1, 4])
        body = json.loads(self.captured_requests[0].data)
        self.assertEqual(
            body["sql"],
            "INSERT INTO fixtures (id, opponent) VALUES (?, ?);\n"
            "INSERT INTO seat_allocations (fixture_id, seat_number) VALUES (?, ?)",
        )
        self.assertEqual(body["params"], ["fix_1", "Reign", "fix_1", 1])

    def test_batch_of_nothing_makes_no_request(self):
        db = LiveD1("acct_1", "db_1", "tok_1")

        import asyncio

        results = asyncio.run(db.batch([]))

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
