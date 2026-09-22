"""A thin wrapper over the AVATARS R2 binding, mirroring db.py's shape.

Kept separate from db.py since R2's calling convention (put/get an object
under a bucket) is different enough from D1's SQL surface that folding it
into the same module would blur what each helper actually talks to.
"""


async def put_object(env, key, data, content_type):
    """Write ``data`` (bytes) to R2 under ``key``, tagging it with
    content_type so a later get_object can hand back the right header."""
    await env.AVATARS.put(key, data, _js_put_options(content_type))


async def get_object(env, key):
    """Return {"bytes", "content_type"} for ``key``, or None if it doesn't
    exist."""
    found = await env.AVATARS.get(key)
    if found is None:
        return None
    buffer = await found.arrayBuffer()
    http_metadata = getattr(found, "httpMetadata", None)
    content_type = getattr(http_metadata, "contentType", None) if http_metadata else None
    return {"bytes": bytes(buffer.to_py()), "content_type": content_type}


def _js_put_options(content_type):
    from js import Object
    from pyodide.ffi import to_js

    return to_js(
        {"httpMetadata": {"contentType": content_type}},
        dict_converter=Object.fromEntries,
    )
