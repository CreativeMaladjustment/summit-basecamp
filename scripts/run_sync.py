#!/usr/bin/env python3
"""Runs the roster/fixture/opponent/headshot sync (src/sync.py) from a
GitHub Actions runner, writing to production D1 over Cloudflare's HTTP API
(d1_http.py) instead of a Workers binding.

Moved out of the Worker (previously POST /api/admin/sync, triggered by
this same repo's .github/workflows/sync-roster.yml) because a Cloudflare
Worker's own fetch() to an external site like nwslsoccer.com originates
from Cloudflare's edge IP space -- one of the most commonly
bot-fingerprinted network ranges on the internet -- so a scrape that fails
from inside the Worker may simply succeed from a GitHub-hosted runner on
an unrelated network. src/sync.py and src/sync_sources.py are otherwise
completely unchanged: live_js_stubs.install() gives `from js import fetch`
a real implementation instead of the Workers one, and d1_http.LiveD1 gives
env.DB the same prepare/bind/all/first/run/batch shape src/db.py already
targets, so nothing in the actual sync logic needed to know it moved.

Required environment variables: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
(the same ones .github/workflows/deploy.yml already uses to apply D1
migrations). The database id is read straight out of wrangler.jsonc's own
d1_databases entry -- the same source of truth deploy.yml's migrations
step ultimately resolves to -- unless CF_D1_DATABASE_ID overrides it.
"""

import asyncio
import json
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import live_js_stubs  # noqa: E402

live_js_stubs.install()

import sync  # noqa: E402
from d1_http import LiveD1  # noqa: E402


def _env_or_die(name):
    value = os.environ.get(name)
    if not value:
        print("::error::{} is not set".format(name), file=sys.stderr)
        sys.exit(1)
    return value


def _database_id():
    override = os.environ.get("CF_D1_DATABASE_ID")
    if override:
        return override
    config_path = os.path.join(ROOT, "wrangler.jsonc")
    with open(config_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    # wrangler.jsonc is JSON with // and /* */ comments allowed -- strip
    # them so it parses as plain JSON, same approach deploy.yml's own
    # detect job already uses for the same file.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    config = json.loads(text)
    databases = config.get("d1_databases") or []
    if not databases:
        print("::error::No d1_databases entry found in wrangler.jsonc", file=sys.stderr)
        sys.exit(1)
    return databases[0]["database_id"]


def main():
    account_id = _env_or_die("CLOUDFLARE_ACCOUNT_ID")
    api_token = _env_or_die("CLOUDFLARE_API_TOKEN")
    database_id = _database_id()

    env = types.SimpleNamespace(DB=LiveD1(account_id, database_id, api_token))
    summary = asyncio.run(sync.run_sync(env))

    print(json.dumps(summary, indent=2))

    failed = [name for name, result in summary.items() if isinstance(result, dict) and "error" in result]
    for name in failed:
        print("::warning::sync job {!r} failed: {}".format(name, summary[name]["error"]))

    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        with open(step_summary_path, "a", encoding="utf-8") as handle:
            handle.write("### Roster sync\n```json\n{}\n```\n".format(json.dumps(summary, indent=2)))

    # A total failure (every job errored) fails the Action loudly, the same
    # signal a non-2xx from the old POST /api/admin/sync gave; a partial one
    # (e.g. only the nwslsoccer.com jobs down, Wikipedia headshots fine)
    # doesn't -- same "one source down doesn't block the rest" run_sync()
    # already applies to the jobs themselves.
    if failed and len(failed) == len(summary):
        sys.exit(1)


if __name__ == "__main__":
    main()
