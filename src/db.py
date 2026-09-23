"""Thin helpers over the D1 binding.

D1 hands results back as JS objects; these helpers convert them to plain
Python dicts so handlers never touch JsProxy values directly.
"""

import secrets
import uuid


def new_id(prefix):
    """Readable, sortable-enough ids, e.g. ``grp_9f2c...``."""
    return "{}_{}".format(prefix, uuid.uuid4().hex[:16])


_INVITE_ADJECTIVES = [
    "amber", "aspen", "basalt", "birch", "blaze", "bold", "brave", "bright",
    "brisk", "calm", "cedar", "clear", "cliff", "cloudy", "cobalt", "coral",
    "cozy", "crisp", "daring", "dawn", "dusty", "eager", "early", "ember",
    "fern", "fleet", "flint", "fresh", "frosty", "gilded", "glacial",
    "golden", "granite", "gritty", "harbor", "hazel", "highland", "hollow",
    "humble", "ivory", "jagged", "jolly", "keen", "lively", "lofty", "lucky",
    "lush", "maple", "meadow", "misty", "mossy", "nimble", "noble", "north",
    "oaken", "olive", "onyx", "opal", "pine", "proud", "quiet", "quick",
    "rapid", "ridge", "rocky", "rowdy", "royal", "rugged", "rustic", "sandy",
    "scarlet", "shady", "silver", "sleepy", "sly", "spruce", "steady",
    "stony", "stormy", "sturdy", "summit", "sunny", "swift", "tidy",
    "timber", "trusty", "tundra", "upbeat", "vast", "vivid", "warm",
    "willow", "windy", "wooly", "zesty",
]
_INVITE_NOUNS = [
    "alpine", "anthem", "arena", "aspen", "attack", "avalanche", "banner",
    "basin", "bench", "boulder", "canyon", "captain", "cedar", "chalet",
    "cinder", "cleats", "cliff", "corner", "crest", "crossbar", "crowd",
    "current", "delta", "divide", "eagle", "echo", "falcon", "field",
    "firepit", "flare", "glacier", "grove", "gully", "harbor", "hawk",
    "hearth", "highland", "horizon", "keeper", "kestrel", "ledge", "lodge",
    "lookout", "meadow", "midfield", "outpost", "overlook", "pass",
    "peak", "pinnacle", "pitch", "plateau", "range", "raven", "ravine",
    "ridge", "river", "rookie", "roster", "saddle", "scout", "signal",
    "slope", "spire", "spruce", "striker", "summit", "supporter",
    "syndicate", "tailgate", "terrace", "thicket", "thunder", "tifo",
    "torrent", "touchline", "trail", "trailhead", "trek", "tundra",
    "tunnel", "valley", "vantage", "vista", "whistle", "wildflower",
    "wingback", "wolfpack",
]


def new_invite_code():
    """A short, easy-to-say two-word code a person can type to join a
    syndicate, e.g. ``AMBER-CANYON`` -- traded down from a 16-hex-character
    code (64 bits) for memorability. That leaves less entropy (95 x 88 word
    pairs, ~13 bits) than would be safe as a lone gate on its own:
    accepted here because it's not one -- this app already sits behind one
    shared site password (see the guest sign-in gate), so a code leaking is a
    lesser event than the site password itself leaking, and
    rotate_invite_code lets an admin kill a leaked or no-longer-wanted code
    instantly. POST /api/groups/join still has no throttling or expiry, so
    don't reuse this generator anywhere a code needs to stand on its own."""
    return "{}-{}".format(
        secrets.choice(_INVITE_ADJECTIVES), secrets.choice(_INVITE_NOUNS)
    ).upper()


def _statement(env, sql, params):
    statement = env.DB.prepare(sql)
    if params:
        statement = statement.bind(*params)
    return statement


def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return row.to_py()


async def query(env, sql, *params):
    """Run a SELECT and return a list of dicts."""
    result = await _statement(env, sql, params).all()
    rows = result.results
    if rows is None:
        return []
    return [_row_to_dict(row) for row in rows]


async def query_one(env, sql, *params):
    """Run a SELECT and return the first row as a dict, or None."""
    row = await _statement(env, sql, params).first()
    return _row_to_dict(row)


async def execute(env, sql, *params):
    """Run an INSERT/UPDATE/DELETE. Returns the number of rows written."""
    result = await _statement(env, sql, params).run()
    meta = result.meta
    if meta is None:
        return 0
    return getattr(meta, "changes", 0) or 0


async def batch(env, statements):
    """Run several writes in one D1 batch (a single implicit transaction).

    ``statements`` is a list of ``(sql, params)`` tuples. Returns the list
    of per-statement results D1 hands back, in order, each shaped like a
    single ``run()`` result (a ``.meta.changes``) -- a caller that needs to
    know whether one specific statement in the batch actually changed a
    row, not just that the batch as a whole didn't raise, can check it
    (see sync._create_fixture_from_sync).
    """
    prepared = [_statement(env, sql, params) for sql, params in statements]
    if not prepared:
        return []
    return await env.DB.batch(prepared)
