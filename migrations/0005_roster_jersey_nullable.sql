-- A player can be on the active roster with no squad number assigned yet
-- (e.g. a recent signing) -- the real Denver Summit FC roster has one right
-- now. jersey_number was NOT NULL with no sentinel for "none", which forced
-- 0 into the column; GET /api/roster passed that 0 straight through as if
-- it were a real number. Rebuild the table (SQLite has no ALTER COLUMN) to
-- allow NULL, converting the existing 0-as-sentinel rows to NULL to match.

CREATE TABLE roster_players_new (
    id TEXT PRIMARY KEY,
    team TEXT NOT NULL DEFAULT 'Denver Summit FC',
    jersey_number INTEGER,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    stats_json TEXT NOT NULL DEFAULT '[]',
    scouting_note TEXT,
    image_path TEXT NOT NULL DEFAULT '/assets/images/players/placeholder-avatar.webp',
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_ref TEXT,
    image_attribution TEXT,
    last_synced_at DATETIME,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO roster_players_new
    (id, team, jersey_number, name, position, stats_json, scouting_note,
     image_path, sort_order, source_ref, image_attribution, last_synced_at, active)
SELECT
    id, team, NULLIF(jersey_number, 0), name, position, stats_json, scouting_note,
    image_path, sort_order, source_ref, image_attribution, last_synced_at, active
FROM roster_players;

DROP TABLE roster_players;
ALTER TABLE roster_players_new RENAME TO roster_players;

CREATE INDEX idx_roster_players_position ON roster_players(position);
CREATE INDEX idx_roster_players_sort ON roster_players(sort_order);
