"""Caller identification and syndicate membership checks.

Sign-in itself (Google/Apple OIDC, minting the session token) is not part of
this scaffold; see ``POST /api/auth/session`` in handlers.py. What is here is
the seam every other endpoint goes through: a bearer token is looked up in the
SESSIONS KV namespace and resolves to a user id.
"""

from db import query_one
from responses import ApiError


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
    # In `wrangler dev` the OIDC round trip is skipped: an X-Dev-User header
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
