"""Reconcile roster, fixture and headshot data against external sources.

Run weekly from the cron in entry.py (`on_scheduled`). Each of the three
jobs below fetches its source through sync_sources, matches what it got
against the existing rows, and writes only what drifted -- existing rows
keep their id and any hand-curated fields (scouting_note, stats_json, ...)
that the source does not speak to.

Matching is by `source_ref` when a row already has one (set the first time
the job successfully matches it), falling back to a name match for rows
that predate the sync job. This is what lets scraping selectors change
without orphaning rows: a later run just needs to find the same name once
more to pick the source_ref back up.

Fixtures are updated in place, never created here -- creating a fixture also
creates its seat_allocations (see handlers.create_fixture), which is an
admin decision this job has no business making on its own. So a remote
fixture with no matching row is skipped, not inserted; only kickoff_at,
venue and source_ref/last_synced_at change on fixtures this job already
knows about.

Headshots: since there is no object storage (see docs/backend.md), a
sync-sourced image is stored as the full Wikimedia Commons URL rather than a
path under frontend/public/assets/images/ -- image_path can hold either a
root-relative asset path (hand-curated images, committed to the repo) or an
absolute https:// URL (sync-sourced). Only images under an
ALLOWED_LICENSE_PREFIXES license are used; anything else leaves the existing
image_path untouched.
"""

from db import execute, new_id, query
from sync_sources import SyncSourceError, fetch_nwsl_roster, fetch_nwsl_schedule, fetch_wikipedia_headshot


async def run_sync(env):
    """Run all three jobs. Each is independent -- one failing does not stop
    the others, since e.g. nwslsoccer.com being unreachable should not also
    block the Wikipedia headshot pass."""
    return {
        "roster": await _safe(_sync_roster, env),
        "fixtures": await _safe(_sync_fixtures, env),
        "opponents": await _safe(_sync_opponents, env),
        "headshots": await _safe(_sync_headshots, env),
    }


async def _safe(job, env):
    try:
        return await job(env)
    except SyncSourceError as error:
        print("Sync job {} skipped: {}".format(job.__name__, error))
        return {"error": str(error)}


async def _sync_roster(env):
    remote_players = await fetch_nwsl_roster(env)
    existing = await query(env, "SELECT id, source_ref, name, jersey_number, position FROM roster_players")
    by_ref = {row["source_ref"]: row for row in existing if row["source_ref"]}
    by_name = {row["name"]: row for row in existing}

    inserted = updated = skipped = 0
    for remote in remote_players:
        row = by_ref.get(remote["source_ref"]) or by_name.get(remote["name"])
        if row is None:
            if remote["jersey_number"] is None:
                # jersey_number is NOT NULL; a roster entry the source page
                # didn't give a number for isn't enough to create a row.
                skipped += 1
                continue
            await execute(
                env,
                """
                INSERT INTO roster_players
                    (id, jersey_number, name, position, source_ref, last_synced_at)
                VALUES (?, ?, ?, ?, ?, DATETIME('now'))
                """,
                new_id("plr"),
                remote["jersey_number"],
                remote["name"],
                remote["position"],
                remote["source_ref"],
            )
            inserted += 1
            continue

        # A source page missing a jersey number shouldn't null out one we
        # already have on file.
        jersey_number = remote["jersey_number"] if remote["jersey_number"] is not None else row["jersey_number"]
        if (
            row["jersey_number"] != jersey_number
            or row["position"] != remote["position"]
            or row["source_ref"] != remote["source_ref"]
        ):
            await execute(
                env,
                """
                UPDATE roster_players
                SET jersey_number = ?, position = ?, source_ref = ?, last_synced_at = DATETIME('now')
                WHERE id = ?
                """,
                jersey_number,
                remote["position"],
                remote["source_ref"],
                row["id"],
            )
            updated += 1
        else:
            await execute(
                env,
                "UPDATE roster_players SET last_synced_at = DATETIME('now') WHERE id = ?",
                row["id"],
            )
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "seen": len(remote_players)}


async def _sync_fixtures(env):
    remote_fixtures = await fetch_nwsl_schedule(env)
    existing = await query(
        env, "SELECT id, source_ref, opponent, kickoff_at, venue FROM fixtures"
    )
    by_ref = {row["source_ref"]: row for row in existing if row["source_ref"]}
    by_opponent_date = {
        (row["opponent"], row["kickoff_at"][:10]): row for row in existing
    }

    updated = matched = 0
    for remote in remote_fixtures:
        row = by_ref.get(remote["source_ref"]) or by_opponent_date.get(
            (remote["opponent"], remote["kickoff_at"][:10])
        )
        if row is None:
            # No admin-created fixture for this match yet -- not this job's
            # place to create one (see module docstring).
            continue
        matched += 1
        if (
            row["kickoff_at"] != remote["kickoff_at"]
            or row["venue"] != remote["venue"]
            or row["source_ref"] != remote["source_ref"]
        ):
            await execute(
                env,
                """
                UPDATE fixtures
                SET kickoff_at = ?, venue = ?, source_ref = ?, last_synced_at = DATETIME('now')
                WHERE id = ?
                """,
                remote["kickoff_at"],
                remote["venue"],
                remote["source_ref"],
                row["id"],
            )
            updated += 1
        else:
            await execute(
                env,
                "UPDATE fixtures SET last_synced_at = DATETIME('now') WHERE id = ?",
                row["id"],
            )
    return {"matched": matched, "updated": updated, "seen": len(remote_fixtures)}


async def _sync_opponents(env):
    """Keep each opponent dossier's next-match dates aligned with the schedule.

    Opponents are club-wide reference rows (see migrations/0002_roster.sql),
    one per club Denver Summit has faced or will face. A club with no
    existing dossier row is skipped, same reasoning as fixtures: the
    scouting content (form, shape_note, quick_stats_json) that makes a
    dossier useful has to come from a human, so this job only keeps the
    dates on dossiers that already exist current.
    """
    remote_fixtures = await fetch_nwsl_schedule(env)
    existing = await query(env, "SELECT id, club, home_date, away_date FROM opponents")
    by_club = {row["club"]: row for row in existing}

    updated = 0
    for remote in remote_fixtures:
        row = by_club.get(remote["opponent"])
        if row is None:
            continue
        date = remote["kickoff_at"][:10]
        field = "home_date" if remote["is_home"] else "away_date"
        if row[field] == date:
            continue
        await execute(
            env,
            "UPDATE opponents SET {} = ?, last_synced_at = DATETIME('now') WHERE id = ?".format(field),
            date,
            row["id"],
        )
        updated += 1
    return {"updated": updated}


async def _sync_headshots(env):
    players = await query(env, "SELECT id, name, image_path FROM roster_players")
    updated = 0
    for player in players:
        headshot = await fetch_wikipedia_headshot(player["name"])
        if headshot is None:
            continue
        if player["image_path"] == headshot["image_url"]:
            continue
        await execute(
            env,
            """
            UPDATE roster_players
            SET image_path = ?, image_attribution = ?, last_synced_at = DATETIME('now')
            WHERE id = ?
            """,
            headshot["image_url"],
            headshot["attribution"],
            player["id"],
        )
        updated += 1
    return {"updated": updated, "checked": len(players)}
