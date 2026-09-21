import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from router import Router  # noqa: E402


def handler_a(request, env, params):
    return "a"


def handler_b(request, env, params):
    return "b"


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = Router()
        self.router.add("GET", "/api/health", handler_a)
        self.router.add("GET", "/api/groups/{group_id}/fixtures", handler_b)
        self.router.add("POST", "/api/groups/{group_id}/fixtures", handler_a)

    def test_matches_a_static_path(self):
        handler, params = self.router.match("GET", "/api/health")
        self.assertIs(handler, handler_a)
        self.assertEqual(params, {})

    def test_captures_path_parameters(self):
        handler, params = self.router.match("GET", "/api/groups/grp_1/fixtures")
        self.assertIs(handler, handler_b)
        self.assertEqual(params, {"group_id": "grp_1"})

    def test_method_picks_between_routes_on_the_same_path(self):
        handler, _ = self.router.match("POST", "/api/groups/grp_1/fixtures")
        self.assertIs(handler, handler_a)

    def test_unknown_path_has_no_allowed_methods(self):
        handler, allowed = self.router.match("GET", "/api/nope")
        self.assertIsNone(handler)
        self.assertEqual(allowed, set())

    def test_known_path_wrong_method_reports_what_is_allowed(self):
        handler, allowed = self.router.match("DELETE", "/api/groups/grp_1/fixtures")
        self.assertIsNone(handler)
        self.assertEqual(allowed, {"GET", "POST"})

    def test_trailing_slashes_are_ignored(self):
        handler, _ = self.router.match("GET", "/api/health/")
        self.assertIs(handler, handler_a)

    def test_a_parameter_matches_one_segment_only(self):
        handler, _ = self.router.match("GET", "/api/groups/a/b/fixtures")
        self.assertIsNone(handler)

    def test_method_is_case_insensitive(self):
        handler, _ = self.router.match("get", "/api/health")
        self.assertIs(handler, handler_a)


if __name__ == "__main__":
    unittest.main()
