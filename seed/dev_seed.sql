-- Local development data. Apply after the migrations:
--   npm run migrate:local && npm run seed:local
--
-- With ENVIRONMENT=development you can call the API as any of these users by
-- sending their id in an X-Dev-User header instead of a bearer token, e.g.
--   curl -H 'X-Dev-User: usr_ada' http://localhost:8787/api/groups

INSERT INTO users (id, email, name, auth_provider, auth_provider_id) VALUES
    ('usr_ada',  'ada@example.com',  'Ada',  'google', 'dev-ada'),
    ('usr_bo',   'bo@example.com',   'Bo',   'google', 'dev-bo'),
    ('usr_cyd',  'cyd@example.com',  'Cyd',  'apple',  'dev-cyd'),
    ('usr_dev',  'dev@example.com',  'Dev',  'google', 'dev-dev');

INSERT INTO groups (id, name, season_year, total_seats, package_cost_cents, created_by) VALUES
    ('grp_summit', 'Summit Hearth & Bench', 2026, 4, 480000, 'usr_ada');

INSERT INTO group_members (group_id, user_id, default_seat_number, role) VALUES
    ('grp_summit', 'usr_ada', 1, 'admin'),
    ('grp_summit', 'usr_bo',  2, 'member'),
    ('grp_summit', 'usr_cyd', 3, 'member'),
    ('grp_summit', 'usr_dev', 4, 'member');

INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, tier, weighted_value_cents) VALUES
    ('fix_001', 'grp_summit', 'Riverside Rovers', DATETIME('now', '+3 days'),  'Summit Park', 'rivalry',  9000),
    ('fix_002', 'grp_summit', 'Northgate FC',     DATETIME('now', '+10 days'), 'Summit Park', 'standard', 5000);

INSERT INTO seat_allocations (id, fixture_id, seat_number, assigned_user_id, status, resale_price_cents) VALUES
    ('seat_001', 'fix_001', 1, 'usr_ada', 'confirmed',     NULL),
    ('seat_002', 'fix_001', 2, 'usr_bo',  'confirmed',     NULL),
    ('seat_003', 'fix_001', 3, NULL,      'on_bench',      NULL),
    ('seat_004', 'fix_001', 4, 'usr_dev', 'resale_listed', 6500),
    ('seat_005', 'fix_002', 1, 'usr_ada', 'confirmed',     NULL),
    ('seat_006', 'fix_002', 2, NULL,      'on_bench',      NULL),
    ('seat_007', 'fix_002', 3, 'usr_cyd', 'confirmed',     NULL),
    ('seat_008', 'fix_002', 4, 'usr_dev', 'confirmed',     NULL);

-- Ada fronted the season package; everyone else owes their quarter.
INSERT INTO transactions (id, group_id, payer_id, recipient_id, amount_cents, description, kind, split_id) VALUES
    ('txn_001', 'grp_summit', 'usr_bo',  'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001'),
    ('txn_002', 'grp_summit', 'usr_cyd', 'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001'),
    ('txn_003', 'grp_summit', 'usr_dev', 'usr_ada', 120000, '2026 season package', 'expense_share', 'split_001');

INSERT INTO player_bios (id, player_name, team, jersey_number, position, bio_markdown, image_path, scheduled_date) VALUES
    ('bio_001', 'Sophia Smith', 'Portland Thorns FC', 9, 'Forward',
     'Explosive off either foot.', '/assets/images/players/smith-sophia.webp', DATE('now')),
    ('bio_002', 'Trinity Rodman', 'Washington Spirit', 2, 'Forward',
     'Relentless on the right.', '/assets/images/players/rodman-trinity.webp', NULL),
    ('bio_003', 'Naomi Girma', 'San Diego Wave FC', 4, 'Defender',
     'Reads the game two passes ahead.', '/assets/images/players/placeholder-avatar.webp', NULL);

INSERT INTO user_notification_prefs (user_id) VALUES
    ('usr_ada'), ('usr_bo'), ('usr_cyd'), ('usr_dev');
