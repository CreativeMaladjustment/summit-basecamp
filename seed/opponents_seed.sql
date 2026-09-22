-- Real Denver Summit FC opponent dossiers only -- safe to run against the
-- production D1 database, unlike seed/dev_seed.sql (which also creates
-- fictional dev users, syndicates, fixtures and tickets that have no place
-- in prod).
--
-- Unlike seed/roster_seed.sql, this one is NOT just an optional bootstrap:
-- src/sync.py's _sync_opponents and _sync_opponent_rosters only ever
-- update an opponent row that already exists (see docs/backend.md for
-- why), the same way fixtures used to work before sync.py gained the
-- ability to create one -- creating an opponent dossier from nothing is
-- still a human decision. So until this file (or an equivalent) has been
-- run once, there is nothing for the sync job to find, and
-- POST /api/admin/sync's opponent_rosters job does nothing at all.
--
-- Idempotent by design, unlike seed/dev_seed.sql's DELETE-then-INSERT: this
-- file gets run against the live production database, possibly more than
-- once (e.g. to pick up a newly-added club, or after fixing a typo here).
-- A DELETE-first approach would wipe opponent_players between runs, but
-- that table is exclusively sync-owned (src/sync.py's
-- _sync_opponent_rosters populates it) -- this file must never touch it.
-- It would also reset any opponent row an admin hand-edited since the last
-- run. So this uses INSERT ... ON CONFLICT DO UPDATE instead, and
-- deliberately leaves form/shape_note out of the UPDATE SET clause: those
-- two columns have no real source yet (see below) and are the columns an
-- admin is most likely to have filled in by hand once one exists, so a
-- rerun of this file must not stomp them back to NULL.
--
-- Run with:
--   npx wrangler d1 execute summit-hearth-db --remote --file=seed/opponents_seed.sql
--
-- All 15 other NWSL clubs (not just Denver Summit's remaining 2026
-- opponents), so the sync job can keep every one current going into next
-- season. source_ref/source_slug are each club's real nwslsoccer.com team
-- id and roster-page slug, both user-verified directly against nwslsoccer.com
-- on 2026-09-22 -- not inferred from a naming pattern, unlike a slug
-- guessed from a club's own name would be (Denver Summit's own case proved
-- that pattern wrong: its match-page slug is "denver-summit", its
-- roster-page slug is "denver-summit-fc"). home_date/away_date/away_venue
-- and match_url (the real page for the most recent meeting) are
-- transcribed from the schedule snapshot also behind
-- web/build_src/data.py's FIXTURES. form and shape_note are left NULL and
-- quick_stats_json empty: no real source for either exists yet, and
-- halftime_note carries the one real, verifiable fact available -- the
-- actual result of the most recent meeting -- rather than invented
-- tactical commentary.

INSERT INTO opponents (id, club, chip_label, home_date, away_date, away_venue, form, shape_note, halftime_note, quick_stats_json, sort_order, source_ref, source_slug, match_url) VALUES
    ('op_angelcity', 'Angel City', 'Angel City · 10/17', '10/17', '9/11', 'BMO Stadium', NULL, NULL, 'Most recent meeting (9/11): Denver drew 3-3 away.', '[]', 0, '9587b8ce40624165903b6bc9fd252634', 'angel-city-fc', 'https://www.nwslsoccer.com/match/6917097b9b664560a221408c048d4257/angel-city-vs-denver-summit'),
    ('op_bay', 'Bay', 'Bay · 9/16', '9/16', '3/14', 'PayPal Park', NULL, NULL, 'Most recent meeting (9/16): Denver drew 2-2 at home.', '[]', 1, '19674698cec24f53af8866cd21abaf8f', 'bay-fc', 'https://www.nwslsoccer.com/match/205368e46d78455f90a1ee09482ea460/denver-summit-vs-bay'),
    ('op_bostonlegacy', 'Boston Legacy', 'Boston Legacy · 8/2', '8/2', '5/3', 'Gillette Stadium', NULL, NULL, 'Most recent meeting (8/2): Denver drew 1-1 at home.', '[]', 2, 'd2d8efe548734dfd8bc667b5a52a079a', 'boston-legacy-fc', 'https://www.nwslsoccer.com/match/e737d2d231134bdb9ab0e3c29b9a64b4/denver-summit-vs-boston-legacy'),
    ('op_chicagostars', 'Chicago Stars', 'Chicago Stars · 10/4', '8/29', '10/4', 'Northwestern Medicine Field at Martin Stadium', NULL, NULL, 'Most recent meeting (8/29): Denver won 6-1 at home.', '[]', 3, '269e825b853f4b43a9d38390aa92bf6e', 'chicago-stars-fc', 'https://www.nwslsoccer.com/match/2f72ffec33184cf09348bbc1481856a5/denver-summit-vs-chicago-stars'),
    ('op_gotham', 'Gotham FC', 'Gotham FC · 9/6', '9/6', '3/25', 'Sports Illustrated Stadium', NULL, NULL, 'Most recent meeting (9/6): Denver won 3-0 at home.', '[]', 4, 'c83f2ca05aa84c738b5373f0d2a31b39', 'gotham-fc', 'https://www.nwslsoccer.com/match/e15415256d81470e9238febd631298c4/denver-summit-vs-gotham-fc'),
    ('op_houstondash', 'Houston Dash', 'Houston Dash · 7/12', '7/12', '5/9', 'Shell Energy Stadium', NULL, NULL, 'Most recent meeting (7/12): Denver drew 2-2 at home.', '[]', 5, 'ca3f464d6b794a9087d441d75961403f', 'houston-dash', 'https://www.nwslsoccer.com/match/81914443c9584c458d9c7b1540667271/denver-summit-vs-houston-dash'),
    ('op_kansascitycu', 'Kansas City Current', 'Kansas City Current · 9/26', '7/3', '9/26', 'CPKC Stadium', NULL, NULL, 'Most recent meeting (7/3): Denver lost 0-3 at home.', '[]', 6, '2c1699409ff84c9eb491aeaca3d3edde', 'kansas-city-current', 'https://www.nwslsoccer.com/match/ec7d28b04d3d4a9ca6d024c41a37702f/denver-summit-vs-kansas-city-current'),
    ('op_northcarolin', 'North Carolina Courage', 'North Carolina Courage · 11/1', '8/5', '11/1', 'First Horizon Stadium at WakeMed Soccer Park', NULL, NULL, 'Most recent meeting (8/5): Denver lost 0-2 at home.', '[]', 7, 'fb41ef4439dd495098cb6d40415767cc', 'north-carolina-courage', 'https://www.nwslsoccer.com/match/b8beb36b96a94acd8f35d2cc14d7e7c1/denver-summit-vs-north-carolina-courage'),
    ('op_orlandopride', 'Orlando Pride', 'Orlando Pride · 5/16', '5/16', '3/20', 'Inter.co Stadium', NULL, NULL, 'Most recent meeting (5/16): Denver won 3-1 at home.', '[]', 8, 'c3e9513e280b41e5bfbb8230076e8c43', 'orlando-pride', 'https://www.nwslsoccer.com/match/b94cd118a1fd4efabe905959b185fe62/denver-summit-vs-orlando-pride'),
    ('op_portlandthor', 'Portland Thorns', 'Portland Thorns · 8/22', '7/18', '8/22', 'Providence Park', NULL, NULL, 'Most recent meeting (8/22): Denver lost 0-1 away.', '[]', 9, '96ba7b37bd8544a1a7329183459150ff', 'portland-thorns-fc', 'https://www.nwslsoccer.com/match/7ac6c3efc9644f7db1e1c8fee444fdb5/portland-thorns-vs-denver-summit'),
    ('op_racinglouisv', 'Racing Louisville', 'Racing Louisville · 10/24', '10/24', '5/29', 'Lynn Family Stadium', NULL, NULL, 'Most recent meeting (5/29): Denver won 1-0 away.', '[]', 10, 'ac29701756da44a08457762380c10733', 'racing-louisville-fc', 'https://www.nwslsoccer.com/match/3bd415d8b50c4025819575e1942de7db/racing-louisville-vs-denver-summit'),
    ('op_sandiegowave', 'San Diego Wave', 'San Diego Wave · 8/14', '4/25', '8/14', 'Snapdragon Stadium', NULL, NULL, 'Most recent meeting (8/14): Denver drew 1-1 away.', '[]', 11, 'ca719042b34443c4bcfe380ca4850eaf', 'san-diego-wave-fc', 'https://www.nwslsoccer.com/match/27b3f650634b411487f905b86f033dab/san-diego-wave-vs-denver-summit'),
    ('op_seattlereign', 'Seattle Reign', 'Seattle Reign · 9/19', '9/19', '4/4', 'One Spokane Stadium', NULL, NULL, 'Most recent meeting (9/19): Denver won 2-1 at home.', '[]', 12, '1151140adfc24339ba1c93cb0b6b0238', 'seattle-reign', 'https://www.nwslsoccer.com/match/3cb04ce8aba14af983e19667197c8b43/denver-summit-vs-seattle-reign'),
    ('op_utahroyals', 'Utah Royals', 'Utah Royals · 8/8', '8/8', '5/23', 'America First Field', NULL, NULL, 'Most recent meeting (8/8): Denver won 2-1 at home.', '[]', 13, 'acffc559cf7d485a9c05fa23ab57054b', 'utah-royals-fc', 'https://www.nwslsoccer.com/match/2ab2e7dd4fbb4a52898ea09d1f99cbdf/denver-summit-vs-utah-royals'),
    ('op_washingtonsp', 'Washington Spirit', 'Washington Spirit · 7/26', '3/28', '7/26', 'Audi Field', NULL, NULL, 'Most recent meeting (7/26): Denver lost 0-1 away.', '[]', 14, 'c31d72afc09f42ee86418633aa41390a', 'washington-spirit', 'https://www.nwslsoccer.com/match/83a606b90fd6443989243fc1e7b160d2/washington-spirit-vs-denver-summit')
ON CONFLICT(id) DO UPDATE SET
    club = excluded.club,
    chip_label = excluded.chip_label,
    home_date = excluded.home_date,
    away_date = excluded.away_date,
    away_venue = excluded.away_venue,
    halftime_note = excluded.halftime_note,
    quick_stats_json = excluded.quick_stats_json,
    sort_order = excluded.sort_order,
    source_ref = excluded.source_ref,
    source_slug = excluded.source_slug,
    match_url = excluded.match_url;
