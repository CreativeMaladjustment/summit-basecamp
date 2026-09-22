-- Local development data. Apply after the migrations:
--   npm run migrate:local && npm run seed:local
--
-- With ENVIRONMENT=development you can call the API as any of these users by
-- sending their id in an X-Dev-User header instead of a bearer token, e.g.
--   curl -H 'X-Dev-User: usr_ada' http://localhost:8787/api/groups

INSERT INTO users (id, email, name, auth_provider, auth_provider_id) VALUES
    ('usr_ada',  'ada@example.com',  'Ada',  'google', 'dev-ada'),
    ('usr_bo',   'bo@example.com',   'Bo',   'google', 'dev-bo'),
    ('usr_cyd',  'cyd@example.com',  'Cyd',  'apple',  'dev-cyd'),
    ('usr_dev',  'dev@example.com',  'Dev',  'google', 'dev-dev');

INSERT INTO groups (id, name, season_year, total_seats, package_cost_cents, created_by) VALUES
    ('grp_summit', 'Summit Hearth & Bench', 2026, 4, 480000, 'usr_ada');

INSERT INTO group_members (group_id, user_id, default_seat_number, role) VALUES
    ('grp_summit', 'usr_ada', 1, 'admin'),
    ('grp_summit', 'usr_bo',  2, 'member'),
    ('grp_summit', 'usr_cyd', 3, 'member'),
    ('grp_summit', 'usr_dev', 4, 'member');

INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, tier, weighted_value_cents) VALUES
    ('fix_001', 'grp_summit', 'Riverside Rovers', DATETIME('now', '+3 days'),  'Summit Park', 'rivalry',  9000),
    ('fix_002', 'grp_summit', 'Northgate FC',     DATETIME('now', '+10 days'), 'Summit Park', 'standard', 5000);

INSERT INTO seat_allocations (id, fixture_id, seat_number, assigned_user_id, status, resale_price_cents) VALUES
    ('seat_001', 'fix_001', 1, 'usr_ada', 'confirmed',     NULL),
    ('seat_002', 'fix_001', 2, 'usr_bo',  'confirmed',     NULL),
    ('seat_003', 'fix_001', 3, NULL,      'on_bench',      NULL),
    ('seat_004', 'fix_001', 4, 'usr_dev', 'resale_listed', 6500),
    ('seat_005', 'fix_002', 1, 'usr_ada', 'confirmed',     NULL),
    ('seat_006', 'fix_002', 2, NULL,      'on_bench',      NULL),
    ('seat_007', 'fix_002', 3, 'usr_cyd', 'confirmed',     NULL),
    ('seat_008', 'fix_002', 4, 'usr_dev', 'confirmed',     NULL);

-- Ada fronted the season package; everyone else owes their quarter.
INSERT INTO transactions (id, group_id, payer_id, recipient_id, amount_cents, description, kind, split_id) VALUES
    ('txn_001', 'grp_summit', 'usr_bo',  'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001'),
    ('txn_002', 'grp_summit', 'usr_cyd', 'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001'),
    ('txn_003', 'grp_summit', 'usr_dev', 'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001');

INSERT INTO player_bios (id, player_name, team, jersey_number, position, bio_markdown, image_path, scheduled_date) VALUES
    ('bio_001', 'Sophia Smith', 'Portland Thorns FC', 9, 'Forward',
     'Explosive off either foot.', '/assets/images/players/smith-sophia.webp', DATE('now')),
    ('bio_002', 'Trinity Rodman', 'Washington Spirit', 2, 'Forward',
     'Relentless on the right.', '/assets/images/players/rodman-trinity.webp', NULL),
    ('bio_003', 'Naomi Girma', 'San Diego Wave FC', 4, 'Defender',
     'Reads the game two passes ahead.', '/assets/images/players/placeholder-avatar.webp', NULL);

INSERT INTO user_notification_prefs (user_id) VALUES
    ('usr_ada'), ('usr_bo'), ('usr_cyd'), ('usr_dev');

-- Home-team squad, backing the Home Team screen (migrations/0002_roster.sql).
-- Transcribed from the official roster at nwslsoccer.com/teams/
-- cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc/roster (2026-09-21
-- snapshot): jersey number, position and nationality only -- the site does
-- not publish season stats or scouting-style bios, so those columns stay
-- factual rather than invented. No headshots: image_path keeps the table's
-- placeholder-avatar default (see web/build_src/data.py for why).
-- Opponent dossiers below (migrations/0002_roster.sql, extended by
-- migrations/0006_opponent_sync.sql) cover all 15 other NWSL clubs with
-- real facts -- see the comment above that INSERT for what's real and what
-- still isn't.
--
-- DELETE first: ids p1-p10 used to belong to the old fictional SQUAD and
-- now name different real players, so a database that already ran the
-- previous version of this seed (rather than being recreated from scratch)
-- would otherwise collide on those primary keys, and any national-team
-- rows still pointing at the reused ids would misattribute caps to whoever
-- now holds p5-p7. Clearing both tables first makes reseeding safe either
-- way.
DELETE FROM national_team_appearances;
DELETE FROM roster_players;

INSERT INTO roster_players (id, team, jersey_number, name, position, stats_json, scouting_note, sort_order) VALUES
    ('p1', 'Denver Summit FC', 1, 'Abby Smith', 'GK', '[["Position", "Goalkeeper"], ["Nationality", "USA"]]', 'Denver Summit FC goalkeeper. See the club''s official roster for 2026 season statistics.', 0),
    ('p2', 'Denver Summit FC', 17, 'Jordan Nytes', 'GK', '[["Position", "Goalkeeper"], ["Nationality", "USA"]]', 'Denver Summit FC goalkeeper. See the club''s official roster for 2026 season statistics.', 1),
    ('p3', 'Denver Summit FC', 36, 'Kat Asman', 'GK', '[["Position", "Goalkeeper"], ["Nationality", "USA"]]', 'Denver Summit FC goalkeeper. See the club''s official roster for 2026 season statistics.', 2),
    ('p4', 'Denver Summit FC', 2, 'Megan Reid', 'DEF', '[["Position", "Defender"], ["Nationality", "CAN"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 3),
    ('p5', 'Denver Summit FC', 3, 'Kaleigh Kurtz', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 4),
    ('p6', 'Denver Summit FC', 4, 'Natalie Means', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 5),
    ('p7', 'Denver Summit FC', 7, 'Ayo Oke', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 6),
    ('p8', 'Denver Summit FC', 13, 'Gemma Bonner', 'DEF', '[["Position", "Defender"], ["Nationality", "ENG"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 7),
    ('p9', 'Denver Summit FC', 16, 'Carson Pickett', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 8),
    ('p10', 'Denver Summit FC', 23, 'Eva Gaetino', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 9),
    ('p11', 'Denver Summit FC', 30, 'Camryn Biegalski', 'DEF', '[["Position", "Defender"], ["Nationality", "USA"]]', 'Denver Summit FC defender. See the club''s official roster for 2026 season statistics.', 10),
    ('p12', 'Denver Summit FC', 5, 'Devin Lynch', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 11),
    ('p13', 'Denver Summit FC', 8, 'Emma Regan', 'MID', '[["Position", "Midfielder"], ["Nationality", "CAN"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 12),
    ('p14', 'Denver Summit FC', 10, 'Lindsey Heaps', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 13),
    ('p15', 'Denver Summit FC', 14, 'Yuna McCormack', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 14),
    ('p16', 'Denver Summit FC', 15, 'Jordan Baggett', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 15),
    ('p17', 'Denver Summit FC', 24, 'Delanie Sheehan', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 16),
    ('p18', 'Denver Summit FC', 34, 'Meg Boade', 'MID', '[["Position", "Midfielder"], ["Nationality", "USA"]]', 'Denver Summit FC midfielder. See the club''s official roster for 2026 season statistics.', 17),
    ('p19', 'Denver Summit FC', 6, 'Janine Sonis', 'FWD', '[["Position", "Forward"], ["Nationality", "CAN"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 18),
    ('p20', 'Denver Summit FC', 9, 'Yazmeen Ryan', 'FWD', '[["Position", "Forward"], ["Nationality", "USA"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 19),
    ('p21', 'Denver Summit FC', 11, 'Ally Brazier', 'FWD', '[["Position", "Forward"], ["Nationality", "USA"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 20),
    ('p22', 'Denver Summit FC', 12, 'Jasmine Aikey', 'FWD', '[["Position", "Forward"], ["Nationality", "USA"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 21),
    ('p23', 'Denver Summit FC', 18, 'Yuzuki Yamamoto', 'FWD', '[["Position", "Forward"], ["Nationality", "JPN"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 22),
    ('p24', 'Denver Summit FC', 25, 'Melissa Kössler', 'FWD', '[["Position", "Forward"], ["Nationality", "DEU"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 23),
    ('p25', 'Denver Summit FC', 26, 'Natasha Flint', 'FWD', '[["Position", "Forward"], ["Nationality", "ENG"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 24),
    ('p26', 'Denver Summit FC', 33, 'Olivia Thomas', 'FWD', '[["Position", "Forward"], ["Nationality", "USA"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 25),
    ('p27', 'Denver Summit FC', 79, 'Nahikari García', 'FWD', '[["Position", "Forward"], ["Nationality", "ESP"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 26),
    ('p28', 'Denver Summit FC', NULL, 'Faith Webber', 'FWD', '[["Position", "Forward"], ["Nationality", "USA"]]', 'Denver Summit FC forward. See the club''s official roster for 2026 season statistics.', 27);

-- All 15 other NWSL clubs, not just Denver Summit's remaining opponents --
-- seeded now so the sync job (src/sync.py _sync_opponent_rosters) can keep
-- every one current going into next season, not just whoever is left on
-- this year's calendar. source_ref/source_slug are each club's real,
-- user-verified nwslsoccer.com team id and roster-page slug (unlike a
-- slug inferred from a club's name, these were confirmed directly, not
-- guessed -- see migrations/0006_opponent_sync.sql for why that distinction
-- matters). home_date/away_date/away_venue and match_url (the real page
-- for the most recent meeting) are transcribed from the same schedule
-- snapshot FIXTURES above comes from. form/shape_note are left NULL and
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
    ('op_washingtonsp', 'Washington Spirit', 'Washington Spirit · 7/26', '3/28', '7/26', 'Audi Field', NULL, NULL, 'Most recent meeting (7/26): Denver lost 0-1 away.', '[]', 14, 'c31d72afc09f42ee86418633aa41390a', 'washington-spirit', 'https://www.nwslsoccer.com/match/83a606b90fd6443989243fc1e7b160d2/washington-spirit-vs-denver-summit');

-- opponent_players is left empty: real per-club rosters come from
-- src/sync.py's _sync_opponent_rosters, using the verified roster URLs
-- above. The old fictional rows here (invented players, "danger" tags on
-- three made-up clubs) are dropped rather than transcribed forward.

-- National-team history (migrations/0003_national_team.sql) is left empty:
-- the roster page (roster_players above) gives current nationality, not cap
-- history, and the previous rows here were invented to match the fictional
-- SQUAD they were seeded alongside. Populate this once a sourced list of
-- senior caps per player exists.
