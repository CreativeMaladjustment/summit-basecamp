-- Backs the Bench screen's release notes and their replies -- previously
-- entirely client-only (web/src/app.js's addBenchNoteCard), so nothing
-- posted there survived a reload or was visible to anyone else. A note is
-- written alongside PATCH /api/seats/{id} setting status='on_bench' (see
-- src/handlers.update_seat): fixture_id/seat_number identify which seat it
-- was posted about, matching seat_allocations' own (fixture_id, seat_number)
-- pairing rather than a foreign key to one specific allocation row, since a
-- seat can be released more than once over a season and each release gets
-- its own note.
CREATE TABLE bench_notes (
    id TEXT PRIMARY KEY,
    fixture_id TEXT NOT NULL REFERENCES fixtures(id),
    seat_number INTEGER NOT NULL,
    author_id TEXT NOT NULL REFERENCES users(id),
    cost_path TEXT NOT NULL DEFAULT 'repay', -- 'repay', 'free'
    amount_cents INTEGER,
    body TEXT NOT NULL,
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bench_notes_fixture ON bench_notes(fixture_id);

CREATE TABLE bench_note_replies (
    id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL REFERENCES bench_notes(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bench_note_replies_note ON bench_note_replies(note_id);
