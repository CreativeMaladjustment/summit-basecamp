-- Real Denver Summit FC roster only -- safe to run against the production
-- D1 database, unlike seed/dev_seed.sql (which also creates fictional dev
-- users, syndicates, fixtures and tickets that have no place in prod).
--
-- This is a stopgap: the weekly sync cron (src/sync.py, wired to run every
-- Monday 5am UTC in wrangler.jsonc) is meant to keep roster_players current
-- automatically, but its scraper (src/sync_sources.py fetch_nwsl_roster)
-- expects a JSON-LD ItemList on the NWSL roster page that the live page
-- does not have -- it fails with SyncSourceError rather than writing
-- anything. Until that scraper is fixed to read the page's actual roster
-- table, this file is the only way real names reach production.
--
-- Run with:
--   npx wrangler d1 execute summit-hearth-db --remote --file=seed/roster_seed.sql
--
-- Transcribed from the official roster at nwslsoccer.com/teams/
-- cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc/roster (2026-09-21
-- snapshot). Season stats and scouting-style bios aren't published there,
-- so those columns stay factual (position, nationality) rather than
-- invented, and no headshots are stored.

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
