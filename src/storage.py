"""A thin wrapper over the AVATARS KV binding, mirroring db.py's shape.

Kept separate from db.py since KV's calling convention (put/get a value
under a key, with side-band metadata) is different enough from D1's SQL
surface that folding it into the same module would blur what each helper
actually talks to.

KV, not R2: R2 needs its own one-time account-level enablement in the
Cloudflare dashboard before any API token can touch it (see
wrangler.jsonc's comment on the AVATARS binding), where KV is already
active on this account -- SESSIONS already uses it -- and a profile
picture (capped well under 1 MiB by handlers.MAX_AVATAR_BYTES) is nowhere
near KV's 25 MiB per-value limit.
"""


async def put_object(env, key, data, content_type):
    """Write ``data`` (bytes) to KV under ``key``, tagging it with
    content_type via KV metadata so a later get_object can hand back the
    right header."""
    await env.AVATARS.put(key, data, _js_put_options(content_type))


async def get_object(env, key):
    """Return {"bytes", "content_type"} for ``key``, or None if it doesn't
    exist."""
    found = await env.AVATARS.getWithMetadata(key, "arrayBuffer")
    value = getattr(found, "value", None) if found is not None else None
    if value is None:
        return None
    metadata = getattr(found, "metadata", None)
    content_type = getattr(metadata, "contentType", None) if metadata else None
    return {"bytes": bytes(value.to_py()), "content_type": content_type}


def _js_put_options(content_type):
    from js import Object
    from pyodide.ffi import to_js

    return to_js(
        {"metadata": {"contentType": content_type}},
        dict_converter=Object.fromEntries,
    )
