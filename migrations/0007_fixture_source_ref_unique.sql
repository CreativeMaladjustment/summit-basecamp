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
CREATE UNIQUE INDEX idx_fixtures_group_source_ref
    ON fixtures(group_id, source_ref)
    WHERE source_ref IS NOT NULL;
