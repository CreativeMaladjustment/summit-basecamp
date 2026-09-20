"""A tiny path router.

Deliberately free of any Workers or JS imports so the matching logic can be
unit-tested with plain CPython.

Patterns use ``{name}`` for a single path segment, e.g.
``/api/groups/{group_id}/fixtures``.
"""


class Router:
    def __init__(self):
        self._routes = []

    def add(self, method, pattern, handler):
        self._routes.append((method.upper(), _split(pattern), handler))
        return handler

    def route(self, method, *patterns):
        """Decorator form: ``@router.route("GET", "/api/health")``."""

        def decorate(handler):
            for pattern in patterns:
                self.add(method, pattern, handler)
            return handler

        return decorate

    def match(self, method, path):
        """Return ``(handler, params)``.

        ``handler`` is None when nothing matched. ``params`` is then the set of
        methods allowed on that path, so the caller can answer 405 rather than
        404 when only the method was wrong.
        """
        segments = _split(path)
        allowed = set()
        for route_method, pattern, handler in self._routes:
            params = _match_segments(pattern, segments)
            if params is None:
                continue
            if route_method == method.upper():
                return handler, params
            allowed.add(route_method)
        return None, allowed


def _split(path):
    return [segment for segment in path.split("/") if segment]


def _match_segments(pattern, segments):
    if len(pattern) != len(segments):
        return None
    params = {}
    for expected, actual in zip(pattern, segments):
        if expected.startswith("{") and expected.endswith("}"):
            params[expected[1:-1]] = actual
        elif expected != actual:
            return None
    return params
