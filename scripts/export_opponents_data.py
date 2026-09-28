#!/usr/bin/env python3
"""Export synced opponent data from D1 database to web/build_src/data.py.

Reads opponents and opponent_players tables and generates the OPPONENTS
Python data structure used by web/build_src/views/visitors.py for
pre-rendering. This is called after sync.py runs to update data.py
with current opponent rosters.

Required environment variables: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
"""

import asyncio
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import live_js_stubs  # noqa: E402

live_js_stubs.install()

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
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    config = json.loads(text)
    databases = config.get("d1_databases") or []
    if not databases:
        print("::error::No d1_databases entry found in wrangler.jsonc", file=sys.stderr)
        sys.exit(1)
    return databases[0]["database_id"]


async def fetch_opponents(db):
    """Fetch all opponents from the database."""
    result = await db.prepare("SELECT * FROM opponents ORDER BY sort_order").all()
    return result.results


async def fetch_opponent_players(db, opponent_id):
    """Fetch all players for an opponent."""
    result = await db.prepare(
        "SELECT * FROM opponent_players WHERE opponent_id = ? AND active ORDER BY sort_order, jersey_number"
    ).bind(opponent_id).all()
    return result.results


async def main():
    account_id = _env_or_die("CLOUDFLARE_ACCOUNT_ID")
    api_token = _env_or_die("CLOUDFLARE_API_TOKEN")
    database_id = _database_id()

    db = LiveD1(account_id, database_id, api_token)

    # Fetch all opponents
    opponents = await fetch_opponents(db)
    if not opponents:
        print("::warning::No opponents found in database")
        return

    # Build OPPONENTS data structure
    opponents_data = []
    for op in opponents:
        # Fetch players for this opponent
        players = await fetch_opponent_players(db, op["id"])

        # Build player list
        player_list = []
        for p in players:
            player_dict = {
                "id": p["id"],
                "num": p["jersey_number"],
                "name": p["name"],
                "pos": p["position"],
                "danger": bool(p["is_danger"]),
                "note": p["scouting_note"] or "",
            }
            player_list.append(player_dict)

        # Build opponent dict
        opponent_dict = {
            "id": op["id"],
            "club": op["club"],
            "chip": op["chip_label"],
            "home_date": op["home_date"],
            "away_date": op["away_date"],
            "away_venue": op["away_venue"],
            "recent_result": op["halftime_note"] or "",
            "match_url": op["match_url"] or "",
            "players": player_list,
        }
        opponents_data.append(opponent_dict)

    # Read current data.py
    data_py_path = os.path.join(ROOT, "web/build_src/data.py")
    with open(data_py_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Build the new OPPONENTS Python code
    opponents_python = "OPPONENTS = [\n"
    for op in opponents_data:
        players_python = "[\n"
        for p in op["players"]:
            players_python += (
                f'        {{"id": {json.dumps(p["id"])}, "num": {p["num"]}, "name": {json.dumps(p["name"])}, '
                f'"pos": {json.dumps(p["pos"])}, "danger": {repr(p["danger"])}, '
                f'"note": {json.dumps(p["note"])}}},\n'
            )
        players_python += "    ]"

        opponents_python += f'''    {{
        "id": {json.dumps(op["id"])}, "club": {json.dumps(op["club"])}, "chip": {json.dumps(op["chip"])},
        "home_date": {json.dumps(op["home_date"])}, "away_date": {json.dumps(op["away_date"])},
        "away_venue": {json.dumps(op["away_venue"])}, "recent_result": {json.dumps(op["recent_result"])},
        "match_url": {json.dumps(op["match_url"])}, "players": {players_python}
    }},
'''
    opponents_python += "]\n"

    # Replace the OPPONENTS list in the file
    new_content = re.sub(
        r"OPPONENTS = \[(.*?)\n\n(?=POSITIONS|$)",
        lambda _: opponents_python + "\n",
        content,
        flags=re.DOTALL
    )

    # Write back to data.py
    with open(data_py_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Exported {len(opponents_data)} opponents to {data_py_path}")


if __name__ == "__main__":
    asyncio.run(main())
