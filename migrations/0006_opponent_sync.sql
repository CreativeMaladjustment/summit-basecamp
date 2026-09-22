-- Extends opponents/opponent_players with the same sync tracking columns
-- migrations/0004_sync_metadata.sql gave roster_players and fixtures, so
-- src/sync.py can reconcile an opponent's real roster the same way it
-- already does the home squad, and match an opponent by nwslsoccer.com's
-- own team id rather than by name alone.
--
-- opponents.source_ref is that team id, discovered for free while parsing
-- the schedule page (see src/sync_sources.fetch_nwsl_schedule) -- the
-- previous claim that opponents have no stable identifier only held before
-- that page's real markup was scraped.
--
-- opponents.source_slug is the second path segment of that team's own
-- nwslsoccer.com roster URL (.../teams/<source_ref>/<source_slug>/roster).
-- Unlike source_ref, this can't be derived from the schedule page --
-- Denver Summit's own slug ("denver-summit-fc") does not match its
-- match-page slug ("denver-summit"), so the same pattern can't be trusted
-- for any other club either. The 15 opponents seeded in
-- seed/opponents_seed.sql carry a verified slug (the real roster URL for
-- each, confirmed directly rather than guessed); a club added later
-- without one is just left unsynced -- see docs/backend.md -- rather than
-- guessed at.
--
-- opponents.match_url is the real, verified nwslsoccer.com match-center
-- link for the most recent meeting between Denver Summit and that club --
-- used as the "Club bio"-equivalent link for an opponent's players on the
-- Visitors screen until real per-player profile links are wired up (see
-- components.bio_links).
ALTER TABLE opponents ADD COLUMN source_ref TEXT;
ALTER TABLE opponents ADD COLUMN source_slug TEXT;
ALTER TABLE opponents ADD COLUMN match_url TEXT;

-- jersey_number becomes nullable for the same reason
-- migrations/0005_roster_jersey_nullable.sql made roster_players.jersey_number
-- nullable: a real player can be on a roster with no squad number assigned
-- yet, and 0 is not a safe stand-in for "none" (see that migration for why).
-- SQLite has no ALTER COLUMN, so this is a table rebuild rather than a
-- second ALTER TABLE.
CREATE TABLE opponent_players_new (
    id TEXT PRIMARY KEY,
    opponent_id TEXT NOT NULL REFERENCES opponents(id),
    jersey_number INTEGER,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    is_danger BOOLEAN NOT NULL DEFAULT FALSE,
    scouting_note TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_ref TEXT,
    last_synced_at DATETIME,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO opponent_players_new
    (id, opponent_id, jersey_number, name, position, is_danger, scouting_note, sort_order)
SELECT id, opponent_id, jersey_number, name, position, is_danger, scouting_note, sort_order
FROM opponent_players;
DROP TABLE opponent_players;
ALTER TABLE opponent_players_new RENAME TO opponent_players;
CREATE INDEX idx_opponent_players_opponent ON opponent_players(opponent_id);
