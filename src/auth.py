"""Caller identification, sign-in, and syndicate membership checks.

Sign-in is a shared-password gate, not per-person auth: everyone types the
same site password (the ``SITE_PWD`` Worker secret) and picks one of six
fixed guest slots seeded by migration 0010. ``verify_site_password`` and
``start_session`` below are used by ``POST /api/auth/session`` in
handlers.py; ``current_user``/``_user_id_from_request`` are the read side
every other endpoint goes through: a bearer token is looked up in the
SESSIONS KV namespace and resolves to a user id.
"""

import hmac
import secrets

from db import query_one
from responses import ApiError

# A guest slot's session outlives a single matchday weekend without being
# forever -- long enough that nobody has to re-enter the shared password
# every visit, short enough that rotating SITE_PWD eventually locks out
# sessions minted under the old one.
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30

# Same lifetime and the same "eventually locks out" property as a session
# token above, for the same reason -- see start_device_trust.
DEVICE_TRUST_TTL_SECONDS = 60 * 60 * 24 * 30


def verify_site_password(env, password):
    """Raise ApiError unless ``password`` matches the SITE_PWD Worker secret.

    Constant-time compare (see trigger_sync's SYNC_ADMIN_TOKEN check for the
    same pattern) -- a naive == would let a timing attack narrow the shared
    password down a character at a time.
    """
    expected = getattr(env, "SITE_PWD", None)
    if not expected:
        raise ApiError(503, "Sign-in is not configured")
    # hmac.compare_digest raises TypeError on anything but str/bytes -- a
    # JSON number or object in the request body would otherwise escape as an
    # uncaught 500 instead of the same 401 any other wrong password gets.
    if not isinstance(password, str) or not hmac.compare_digest(password, expected):
        raise ApiError(401, "Wrong password")


async def start_device_trust(env):
    """Mint an opaque token proving this device already passed the site
    password once, and write it into SESSIONS KV as ``device:<token>``.

    This is what a device remembers instead of the password itself (see
    ``begin_session``) -- an opaque, server-issued, independently revocable
    credential, not the literal shared secret sitting in the browser's own
    storage for any script on the page to read.
    """
    token = secrets.token_hex(32)
    await env.SESSIONS.put("device:" + token, "1", _ttl_options(DEVICE_TRUST_TTL_SECONDS))
    return token


async def verify_device_token(env, device_token):
    """Raise ApiError unless ``device_token`` is a still-valid device-trust
    token from start_device_trust."""
    if not isinstance(device_token, str):
        raise ApiError(401, "Device is no longer trusted -- enter the site password again")
    trusted = await env.SESSIONS.get("device:" + device_token)
    if not trusted:
        raise ApiError(401, "Device is no longer trusted -- enter the site password again")


async def start_session(env, user_id):
    """Mint a bearer token for ``user_id`` and write it into SESSIONS KV --
    the write side of _user_id_from_request's lookup below."""
    token = secrets.token_hex(32)
    await env.SESSIONS.put("session:" + token, user_id, _ttl_options(SESSION_TTL_SECONDS))
    return token


def _ttl_options(ttl_seconds):
    from js import Object
    from pyodide.ffi import to_js

    return to_js({"expirationTtl": ttl_seconds}, dict_converter=Object.fromEntries)


async def current_user(request, env):
    """Return the signed-in user as a dict, or raise ApiError(401)."""
    user_id = await _user_id_from_request(request, env)
    if not user_id:
        raise ApiError(401, "Sign in to continue")

    user = await query_one(env, "SELECT * FROM users WHERE id = ?", user_id)
    if user is None:
        raise ApiError(401, "Session refers to a user that no longer exists")
    return user


async def _user_id_from_request(request, env):
    # In `wrangler dev` a real sign-in is skipped: an X-Dev-User header
    # names the user directly. This is refused outside development.
    if env.ENVIRONMENT == "development":
        dev_user = request.headers.get("X-Dev-User")
        if dev_user:
            return dev_user

    header = request.headers.get("Authorization") or ""
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer ") :].strip()
    if not token:
        return None
    return await env.SESSIONS.get("session:" + token)


async def require_membership(env, group_id, user_id):
    """Return the caller's membership row, or raise ApiError(403)."""
    membership = await query_one(
        env,
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        group_id,
        user_id,
    )
    if membership is None:
        raise ApiError(403, "You are not a member of this syndicate")
    return membership


async def require_admin(env, group_id, user_id):
    membership = await require_membership(env, group_id, user_id)
    if membership.get("role") != "admin":
        raise ApiError(403, "Only a syndicate admin can do this")
    return membership
