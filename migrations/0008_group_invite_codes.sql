-- Summit Basecamp — invite codes, so a signed-in user can join an existing
-- syndicate by code instead of an admin adding them by hand.
ALTER TABLE groups ADD COLUMN invite_code TEXT;

-- Backfill any syndicate that existed before this column did. New rows
-- always set their own code at INSERT time (see handlers.create_group); this
-- only covers rows already in the database when this migration runs.
UPDATE groups
SET invite_code = upper(substr(hex(randomblob(8)), 1, 8))
WHERE invite_code IS NULL;

CREATE UNIQUE INDEX idx_groups_invite_code ON groups(invite_code);
