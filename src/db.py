"""Thin helpers over the D1 binding.

D1 hands results back as JS objects; these helpers convert them to plain
Python dicts so handlers never touch JsProxy values directly.
"""

import uuid


def new_id(prefix):
    """Readable, sortable-enough ids, e.g. ``grp_9f2c...``."""
    return "{}_{}".format(prefix, uuid.uuid4().hex[:16])


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
