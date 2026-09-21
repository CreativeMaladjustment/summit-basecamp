-- Whether a home-squad player is a current or former national-team player,
-- and which years -- floutenvy asked for this on the Home Team roster.
--
-- One row per stint rather than a single column, since a player can have
-- represented more than one country, or the same one more than once, over a
-- career; "current" is just the row with no year_end yet.

CREATE TABLE national_team_appearances (
    id TEXT PRIMARY KEY,
    player_id TEXT REFERENCES roster_players(id),
    country TEXT NOT NULL,
    year_start INTEGER NOT NULL,
    year_end INTEGER, -- NULL means still capped as of today
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_national_team_player ON national_team_appearances(player_id);
