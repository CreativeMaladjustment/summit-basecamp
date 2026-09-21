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

-- Home-team squad and opponent dossiers, backing the Home Team and Visitors
-- screens (migrations/0002_roster.sql). Transcribed one-for-one from the
-- data that used to be baked into the frontend build
-- (web/build_src/data.py: SQUAD, OPPONENTS).

INSERT INTO roster_players (id, team, jersey_number, name, position, stats_json, scouting_note, sort_order) VALUES
    ('p1', 'Denver Summit FC', 1, 'Rowan Vasquez', 'GK', '[["Clean sheets", "7"], ["Saves", "54"], ["Starts", "19"]]', 'Comes for everything in the six. The Hearth breathes easier when she claims the first cross.', 0),
    ('p2', 'Denver Summit FC', 4, 'Imani Brooks', 'DEF', '[["Tackles", "48"], ["Duels won", "62%"], ["Starts", "21"]]', 'Steps in front of the pass rather than chasing it. Reads the game a beat early.', 1),
    ('p3', 'Denver Summit FC', 5, 'Freja Lindholm', 'DEF', '[["Clearances", "71"], ["Aerials", "58%"], ["Starts", "20"]]', 'The bench captain in everything but the armband. Organises the line from kickoff.', 2),
    ('p4', 'Denver Summit FC', 6, 'Priya Raman', 'MID', '[["Passes", "1,204"], ["Accuracy", "88%"], ["Starts", "22"]]', 'Sets the tempo the way you bank a fire — quietly, and all night.', 3),
    ('p5', 'Denver Summit FC', 8, 'Nadia Okafor', 'MID', '[["Assists", "9"], ["Key passes", "41"], ["Starts", "18"]]', 'Finds the runner nobody else saw. Watch her shoulders, not the ball.', 4),
    ('p6', 'Denver Summit FC', 10, 'Sloane Beckett', 'MID', '[["Goals", "6"], ["Assists", "11"], ["Starts", "21"]]', 'Drops off the front line to collect, then turns. The whole attack pivots on that turn.', 5),
    ('p7', 'Denver Summit FC', 9, 'Tess Aldridge', 'FWD', '[["Goals", "14"], ["Shots/90", "3.8"], ["Starts", "22"]]', 'Runs the channel until the centre-back blinks. Fourteen goals say the blink comes.', 6),
    ('p8', 'Denver Summit FC', 11, 'Juno Park', 'FWD', '[["Goals", "8"], ["Dribbles", "63"], ["Starts", "17"]]', 'Takes the outside shoulder every time, and it works roughly every third time.', 7),
    ('p9', 'Denver Summit FC', 17, 'Camille Duarte', 'FWD', '[["Goals", "5"], ["Sub apps", "14"], ["Minutes", "612"]]', 'The sub who changes the temperature. Rarely starts, often decides.', 8),
    ('p10', 'Denver Summit FC', 23, 'Harper Nakamura', 'DEF', '[["Interceptions", "39"], ["Crosses", "52"], ["Starts", "16"]]', 'Overlaps into the space Juno vacates. The two of them read each other well.', 9);

INSERT INTO opponents (id, club, chip_label, home_date, away_date, away_venue, form, shape_note, halftime_note, quick_stats_json, sort_order) VALUES
    ('op_por', 'Portland Thorns', 'Portland · 9/26', '9/26', '5/9', 'Providence Park', 'W W D L W', '4-3-3, inverted right back, high line they will not drop.', 'They press the goal kick for twenty minutes and then stop. Play through the first twenty and the second half opens up.', '[["Goals for", "31"], ["Goals against", "19"], ["Away wins", "5"]]', 0),
    ('op_bay', 'Bay FC', 'Bay · 10/3', '10/3', '6/20', 'PayPal Park', 'L D W L D', '4-4-2 block, counters through the left channel.', 'They sit, they absorb, and they break once. Keep a body on the counter and the afternoon is comfortable.', '[["Goals for", "22"], ["Goals against", "26"], ["Away wins", "2"]]', 1),
    ('op_acf', 'Angel City FC', 'Angel City · 10/18', '10/18', '7/11', 'BMO Stadium', 'W W W D W', '3-4-3, wing-backs high, three at the back that can be turned.', 'The wing-backs are still up the pitch at 60 minutes. That is when the diagonal behind them is on.', '[["Goals for", "36"], ["Goals against", "17"], ["Away wins", "7"]]', 2);

INSERT INTO opponent_players (id, opponent_id, jersey_number, name, position, is_danger, scouting_note, sort_order) VALUES
    ('o1', 'op_por', 9, 'Marisol Vega', 'FWD', 1, 'Every dangerous move starts with her drifting to the left half-space. Track it or lose the game.', 0),
    ('o2', 'op_por', 6, 'Elin Sandberg', 'MID', 0, 'Screens the back four. Slow across the ground — go at her sideways, not through her.', 1),
    ('o3', 'op_por', 2, 'Dara Whitfield', 'DEF', 0, 'Overlaps constantly and recovers late. The space behind her is the game.', 2),
    ('o4', 'op_bay', 11, 'Noor Haddad', 'FWD', 1, 'The one who hurts you on the break. Nine of her twelve goals came inside four passes.', 0),
    ('o5', 'op_bay', 8, 'Robin Castellanos', 'MID', 0, 'Takes every set piece. Left foot, near post, in-swinging.', 1),
    ('o6', 'op_bay', 1, 'Ada Lindgren', 'GK', 0, 'Strong hands, hesitant feet. Press the back pass.', 2),
    ('o7', 'op_acf', 7, 'Céline Abara', 'FWD', 1, 'Best player on either team most weeks. Double her the moment she faces up.', 0),
    ('o8', 'op_acf', 3, 'Wren Okonkwo', 'DEF', 0, 'Left of the three. Comfortable stepping in, uncomfortable turning.', 1),
    ('o9', 'op_acf', 16, 'Tamsin Reyes', 'MID', 0, 'Runs the whole game at one speed. Tires after 70.', 2);
