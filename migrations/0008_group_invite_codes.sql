-- Summit Basecamp — invite codes, so a signed-in user can join an existing
-- syndicate by code instead of an admin adding them by hand.
ALTER TABLE groups ADD COLUMN invite_code TEXT;

-- Backfill any syndicate that existed before this column did. 16 hex
-- characters (64 bits), same as db.new_invite_code -- see there for why a
-- join code needs real entropy, not just db.new_id's shorter cousin.
UPDATE groups
SET invite_code = upper(hex(randomblob(8)))
WHERE invite_code IS NULL;

CREATE UNIQUE INDEX idx_groups_invite_code ON groups(invite_code);
