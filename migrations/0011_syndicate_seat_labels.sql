-- Physical seat details for a syndicate: which section the whole package
-- sits in, its row, and the real seat numbers within it (freeform text,
-- e.g. "3, 4") -- distinct from group_members.default_seat_number and
-- seat_allocations.seat_number, which stay an internal 1..total_seats
-- index used to assign and track seats, not what's printed on the ticket.
-- "row" is a reserved SQLite keyword, hence seat_row rather than row.
-- group_members.seat_label is which one of a syndicate's real seat_labels
-- is this member's own.
ALTER TABLE groups ADD COLUMN section TEXT;
ALTER TABLE groups ADD COLUMN seat_row TEXT;
ALTER TABLE groups ADD COLUMN seat_labels TEXT;
ALTER TABLE group_members ADD COLUMN seat_label TEXT;
