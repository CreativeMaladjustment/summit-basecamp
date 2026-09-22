-- Makes sync.py's fixture creation (_create_fixture_from_sync) safe against
-- two overlapping sync runs -- .github/workflows/sync-roster.yml fires on
-- both a deploy and its own weekly schedule, and POST /api/admin/sync can
-- also be called by hand, so two runs racing each other is a real
-- possibility, not just theoretical. Without this, both could observe the
-- same group missing the same real-world match and each insert their own
-- fixture (and seat_allocations) for it.
--
-- Partial index, not a plain UNIQUE column: source_ref is NULL for
-- fixtures an admin created by hand (create_fixture never sets it), and
-- multiple NULLs must stay allowed -- only two rows that both claim the
-- same synced match for the same group should be rejected.
--
-- Collapse existing duplicates first, or CREATE UNIQUE INDEX itself fails
-- on any database that already has one: the pre-0007 sync could set the
-- same source_ref on more than one row in a single run (a name+date-window
-- match against several not-yet-synced rows for the same group and
-- opponent), and handlers.create_fixture has never itself stopped an
-- admin from creating duplicate fixtures by hand either. Keeping the
-- lowest id per (group_id, source_ref) is an arbitrary but stable choice
-- -- nothing here distinguishes which duplicate is "more correct" -- and
-- its seats go with it; the kept row's own seats are untouched.
DELETE FROM seat_allocations
WHERE fixture_id IN (
    SELECT id FROM fixtures
    WHERE source_ref IS NOT NULL
    AND id NOT IN (
        SELECT MIN(id) FROM fixtures WHERE source_ref IS NOT NULL GROUP BY group_id, source_ref
    )
);
DELETE FROM fixtures
WHERE source_ref IS NOT NULL
AND id NOT IN (
    SELECT MIN(id) FROM fixtures WHERE source_ref IS NOT NULL GROUP BY group_id, source_ref
);

CREATE UNIQUE INDEX idx_fixtures_group_source_ref
    ON fixtures(group_id, source_ref)
    WHERE source_ref IS NOT NULL;
