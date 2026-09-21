-- Home-team squad and opponent dossiers, backing the Home Team and Visitors
-- screens. Both currently render from data baked into the frontend build
-- (web/build_src/data.py: SQUAD, OPPONENTS), which had no API behind it at all.
--
-- These are club-wide reference data, not scoped to a syndicate (`group`),
-- so there is no group_id here -- every syndicate sees the same roster.

CREATE TABLE roster_players (
    id TEXT PRIMARY KEY,
    team TEXT NOT NULL DEFAULT 'Denver Summit FC',
    jersey_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    position TEXT NOT NULL, -- 'GK', 'DEF', 'MID', 'FWD'
    -- JSON array of [label, value] pairs, e.g. [["Goals","14"],["Starts","22"]].
    -- Stat labels vary by position, so this stays free-form rather than a
    -- fixed set of columns.
    stats_json TEXT NOT NULL DEFAULT '[]',
    scouting_note TEXT,
    image_path TEXT NOT NULL DEFAULT '/assets/images/players/placeholder-avatar.webp',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_roster_players_position ON roster_players(position);
CREATE INDEX idx_roster_players_sort ON roster_players(sort_order);

CREATE TABLE opponents (
    id TEXT PRIMARY KEY,
    club TEXT NOT NULL,
    chip_label TEXT NOT NULL,
    home_date TEXT,
    away_date TEXT,
    away_venue TEXT,
    form TEXT,
    shape_note TEXT,
    halftime_note TEXT,
    -- JSON array of [label, value] pairs, e.g. [["Goals for","31"],...].
    quick_stats_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_opponents_sort ON opponents(sort_order);

CREATE TABLE opponent_players (
    id TEXT PRIMARY KEY,
    opponent_id TEXT NOT NULL REFERENCES opponents(id),
    jersey_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    is_danger BOOLEAN NOT NULL DEFAULT FALSE,
    scouting_note TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_opponent_players_opponent ON opponent_players(opponent_id);
