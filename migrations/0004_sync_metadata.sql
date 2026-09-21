-- Tracking columns for the automated roster/fixture/headshot sync job
-- (src/sync.py, run from the weekly cron in src/entry.py).
--
-- source_ref is the external identifier the sync job matched a row against
-- (an NWSL roster/schedule slug) so re-runs update the same row instead of
-- guessing again from name alone. last_synced_at records when the job last
-- confirmed the row still matches its source, so a row that predates the
-- sync job (last_synced_at IS NULL) can be told apart from one the job has
-- already reconciled at least once.
--
-- opponents has no source_ref: nwslsoccer.com's schedule data gives no
-- stable per-club identifier, only the club name, which is already how
-- opponents are matched -- a column that could never be populated would
-- just be documentation nobody could trust.

ALTER TABLE roster_players ADD COLUMN source_ref TEXT;
ALTER TABLE roster_players ADD COLUMN image_attribution TEXT;
ALTER TABLE roster_players ADD COLUMN last_synced_at DATETIME;
-- Cleared by the sync job when a player drops off the remote roster, rather
-- than deleting the row, so past stats and national_team_appearances stay
-- intact. GET /api/roster only returns active players.
ALTER TABLE roster_players ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE fixtures ADD COLUMN source_ref TEXT;
ALTER TABLE fixtures ADD COLUMN last_synced_at DATETIME;

ALTER TABLE opponents ADD COLUMN last_synced_at DATETIME;
