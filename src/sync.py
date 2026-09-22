"""Reconcile roster, fixture and headshot data against external sources.

Run weekly from the cron in entry.py (`on_scheduled`). Each of the three
jobs below fetches its source through sync_sources, matches what it got
against the existing rows, and writes only what drifted -- existing rows
keep their id and any hand-curated fields (scouting_note, stats_json, ...)
that the source does not speak to. A source field that came back empty
(missing jersey number, missing position, missing venue) never overwrites an
existing value with a blank -- it just means that field didn't drift.

Matching is by `source_ref` when a row already has one (set the first time
the job successfully matches it), falling back to a name match for rows
that predate the sync job. This is what lets scraping selectors change
without orphaning rows: a later run just needs to find the same name once
more to pick the source_ref back up.

Fixtures this job already knows about are only ever updated -- kickoff_at,
venue and source_ref/last_synced_at -- never their tier or
weighted_value_cents, which stay an admin's call. Fixtures are scoped per
syndicate (group_id), so more than one group can each have their own row
for the same real-world match; every matching row is updated, not just one.

An upcoming *home* match with no matching row in a given group does get a
new fixture created for that group (every seat starting on the bench,
unassigned -- see _create_fixture_from_sync), one per group missing it, so
a newly announced or rescheduled-into-range home game shows up without an
admin adding it by hand first. Away matches never create a fixture: this
app only ever sells seats at the home venue, so an away leg has no seat
package to represent. Neither does a match that has already kicked off --
there is nothing left to claim on it.

Headshots: since there is no object storage (see docs/backend.md), a
sync-sourced image is stored as the full Wikimedia Commons URL rather than a
path under frontend/public/assets/images/ -- image_path can hold either a
root-relative asset path (hand-curated images, committed to the repo) or an
absolute https:// URL (sync-sourced). Only images under an
ALLOWED_LICENSE_PREFIXES license are used; anything else leaves the existing
image_path untouched.
"""

import datetime

from db import batch, execute, new_id, query
from sync_sources import SyncSourceError, fetch_nwsl_roster, fetch_nwsl_schedule, fetch_wikipedia_headshot

# How far a fixture's remote kickoff date may drift from what's on file and
# still be considered the same match, the first time a row is matched (before
# it has a source_ref). Wide enough to catch a real reschedule (typically
# days, occasionally a couple of weeks for a broadcast move), narrow enough
# that two fixtures against the same opponent in one season -- home and away,
# normally months apart -- don't collide.
FIXTURE_REMATCH_WINDOW = datetime.timedelta(days=21)


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
    """Insert/update against the remote roster, then deactivate anyone left
    off it -- a full roster listing implies anyone not on it has departed.
    Deactivating rather than deleting keeps their history (national-team
    caps, past stats) intact; handlers.list_roster filters to active rows.
    """
    remote_players = await fetch_nwsl_roster(env)
    existing = await query(
        env, "SELECT id, source_ref, name, jersey_number, position, active FROM roster_players"
    )
    by_ref = {row["source_ref"]: row for row in existing if row["source_ref"]}
    by_name = {row["name"]: row for row in existing}

    inserted = updated = skipped = reactivated = 0
    seen_ids = set()
    for remote in remote_players:
        row = by_ref.get(remote["source_ref"]) or by_name.get(remote["name"])
        if row is None:
            if remote["jersey_number"] is None or not remote["position"]:
                # jersey_number and position are both required to be useful;
                # a roster entry the source page didn't give one for isn't
                # enough to create a row from scratch.
                skipped += 1
                continue
            new_row_id = new_id("plr")
            await execute(
                env,
                """
                INSERT INTO roster_players
                    (id, jersey_number, name, position, source_ref, last_synced_at)
                VALUES (?, ?, ?, ?, ?, DATETIME('now'))
                """,
                new_row_id,
                remote["jersey_number"],
                remote["name"],
                remote["position"],
                remote["source_ref"],
            )
            inserted += 1
            seen_ids.add(new_row_id)
            continue

        seen_ids.add(row["id"])
        # A source page missing a jersey number or position shouldn't null
        # out one we already have on file.
        jersey_number = remote["jersey_number"] if remote["jersey_number"] is not None else row["jersey_number"]
        position = remote["position"] or row["position"]
        if (
            row["jersey_number"] != jersey_number
            or row["position"] != position
            or row["name"] != remote["name"]
            or row["source_ref"] != remote["source_ref"]
            or not row["active"]
        ):
            if not row["active"]:
                reactivated += 1
            await execute(
                env,
                """
                UPDATE roster_players
                SET jersey_number = ?, position = ?, name = ?, source_ref = ?,
                    active = TRUE, last_synced_at = DATETIME('now')
                WHERE id = ?
                """,
                jersey_number,
                position,
                remote["name"],
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

    deactivated = 0
    still_active = [row["id"] for row in existing if row["id"] not in seen_ids and row["active"]]
    for player_id in still_active:
        await execute(env, "UPDATE roster_players SET active = FALSE WHERE id = ?", player_id)
        deactivated += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "reactivated": reactivated,
        "deactivated": deactivated,
        "seen": len(remote_players),
    }


async def _sync_fixtures(env):
    remote_fixtures = await fetch_nwsl_schedule(env)
    existing = await query(
        env, "SELECT id, group_id, source_ref, opponent, kickoff_at, venue FROM fixtures"
    )
    by_ref = {}
    for row in existing:
        if row["source_ref"]:
            by_ref.setdefault(row["source_ref"], []).append(row)
    unmatched = [row for row in existing if not row["source_ref"]]

    groups = await query(env, "SELECT id, total_seats FROM groups")
    today = datetime.date.today()

    updated = matched = created = 0
    for remote in remote_fixtures:
        rows = by_ref.get(remote["source_ref"])
        if rows is None:
            # First time this fixture is seen: match any not-yet-synced row
            # for the same opponent within the rematch window, regardless of
            # group -- several syndicates can each hold their own fixture
            # row for the same real-world match.
            remote_date = _parse_date(remote["kickoff_at"])
            rows = [
                row
                for row in unmatched
                if row["opponent"] == remote["opponent"]
                and _within_window(remote_date, _parse_date(row["kickoff_at"]))
            ]
            for row in rows:
                unmatched.remove(row)
        for row in rows:
            matched += 1
            venue = remote["venue"] or row["venue"]
            if (
                row["kickoff_at"] != remote["kickoff_at"]
                or row["venue"] != venue
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
                    venue,
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

        # A home match still ahead of kickoff gets a fresh fixture (every
        # seat unassigned) in every group that doesn't already have a row
        # for it -- see the module docstring for why away/past matches
        # never do.
        if not remote["is_home"]:
            continue
        remote_date = _parse_date(remote["kickoff_at"])
        if remote_date is None or remote_date < today:
            continue
        matched_group_ids = {row["group_id"] for row in rows}
        for group in groups:
            if group["id"] in matched_group_ids:
                continue
            await _create_fixture_from_sync(env, group, remote)
            created += 1

    return {"matched": matched, "updated": updated, "created": created, "seen": len(remote_fixtures)}


async def _create_fixture_from_sync(env, group, remote):
    """Insert a fixture the sync found with no matching row yet in this
    group, every seat starting unassigned and on the bench.

    Unlike handlers.create_fixture, this never pre-assigns a member's
    default seat: that pre-assignment stands in for "this is who normally
    sits here," which is a reasonable default when an admin deliberately
    adds a fixture, but not for one this job invented on its own -- nobody
    has claimed anything on a fixture nobody asked for yet. tier and
    weighted_value_cents get placeholders (a source page has no idea what
    your group's package costs); an admin corrects both by hand.
    """
    fixture_id = new_id("fix")
    writes = [
        (
            """
            INSERT INTO fixtures
                (id, group_id, opponent, kickoff_at, venue, tier,
                 weighted_value_cents, source_ref, last_synced_at)
            VALUES (?, ?, ?, ?, ?, 'standard', 0, ?, DATETIME('now'))
            """,
            (
                fixture_id,
                group["id"],
                remote["opponent"],
                remote["kickoff_at"],
                remote["venue"],
                remote["source_ref"],
            ),
        )
    ]
    for seat_number in range(1, int(group["total_seats"]) + 1):
        writes.append(
            (
                "INSERT INTO seat_allocations (id, fixture_id, seat_number, status) VALUES (?, ?, ?, 'on_bench')",
                (new_id("seat"), fixture_id, seat_number),
            )
        )
    await batch(env, writes)


def _parse_date(kickoff_at):
    try:
        return datetime.datetime.fromisoformat(kickoff_at).date()
    except ValueError:
        return None


def _within_window(remote_date, existing_date):
    if remote_date is None or existing_date is None:
        return False
    return abs(remote_date - existing_date) <= FIXTURE_REMATCH_WINDOW


async def _sync_opponents(env):
    """Keep each opponent dossier's next-match dates aligned with the schedule.

    Opponents are club-wide reference rows (see migrations/0002_roster.sql),
    one per club Denver Summit has faced or will face. A club with no
    existing dossier row is skipped, same reasoning as fixtures: the
    scouting content (form, shape_note, quick_stats_json) that makes a
    dossier useful has to come from a human, so this job only keeps the
    dates on dossiers that already exist current.

    Matched by club name only -- nwslsoccer.com's schedule JSON-LD gives no
    other stable identifier for the opponent team (see fetch_nwsl_schedule),
    so a club rename upstream would need a manual re-match here; there's
    nothing to key a source_ref off in the meantime.
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
    players = await query(env, "SELECT id, name, image_path FROM roster_players WHERE active")
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
