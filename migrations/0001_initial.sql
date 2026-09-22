-- Summit Basecamp — initial D1 schema.
--
-- Naming follows the design export: a syndicate is a `group`, a seat for one
-- fixture is a `seat_allocation`, and every money movement is a row in
-- `transactions`. A resale listing is not its own table: it is a seat
-- allocation whose status is 'resale_listed' with a resale_price_cents.

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    avatar_url TEXT,
    auth_provider TEXT NOT NULL, -- 'google' or 'apple'
    auth_provider_id TEXT NOT NULL, -- subject ID from the OIDC token
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_users_provider ON users(auth_provider, auth_provider_id);
CREATE UNIQUE INDEX idx_users_email ON users(email);

CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    season_year INTEGER NOT NULL,
    total_seats INTEGER NOT NULL,
    package_cost_cents INTEGER NOT NULL,
    created_by TEXT REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_groups_season ON groups(season_year);

CREATE TABLE group_members (
    group_id TEXT REFERENCES groups(id),
    user_id TEXT REFERENCES users(id),
    default_seat_number INTEGER,
    role TEXT DEFAULT 'member', -- 'admin', 'member'
    PRIMARY KEY(group_id, user_id)
);
CREATE INDEX idx_group_members_user ON group_members(user_id);

CREATE TABLE fixtures (
    id TEXT PRIMARY KEY,
    group_id TEXT REFERENCES groups(id),
    opponent TEXT NOT NULL,
    kickoff_at DATETIME NOT NULL,
    venue TEXT NOT NULL,
    tier TEXT DEFAULT 'standard', -- 'rivalry', 'standard', 'cup'
    weighted_value_cents INTEGER NOT NULL
);
CREATE INDEX idx_fixtures_kickoff ON fixtures(kickoff_at);
CREATE INDEX idx_fixtures_group ON fixtures(group_id);

CREATE TABLE seat_allocations (
    id TEXT PRIMARY KEY,
    fixture_id TEXT REFERENCES fixtures(id),
    seat_number INTEGER NOT NULL,
    assigned_user_id TEXT REFERENCES users(id),
    status TEXT DEFAULT 'confirmed', -- 'confirmed', 'on_bench', 'gifted', 'resale_listed'
    guest_name TEXT,
    resale_price_cents INTEGER,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_allocations_seat ON seat_allocations(fixture_id, seat_number);
CREATE INDEX idx_allocations_fixture ON seat_allocations(fixture_id);
CREATE INDEX idx_allocations_user ON seat_allocations(assigned_user_id);
CREATE INDEX idx_allocations_status ON seat_allocations(status);

-- The ledger. An expense split writes one row per member who owes a share,
-- all sharing a split_id so the split can be shown or reversed as one unit.
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    group_id TEXT REFERENCES groups(id),
    payer_id TEXT REFERENCES users(id),
    recipient_id TEXT REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    description TEXT,
    kind TEXT DEFAULT 'expense_share', -- 'expense_share', 'seat_payout', 'settlement'
    split_id TEXT,
    settled BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_transactions_group ON transactions(group_id);
CREATE INDEX idx_transactions_split ON transactions(split_id);
CREATE INDEX idx_transactions_unsettled ON transactions(group_id, settled);

CREATE TABLE player_bios (
    id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    jersey_number INTEGER,
    position TEXT,
    bio_markdown TEXT,
    -- Root-relative path to an asset committed under
    -- frontend/public/assets/images/ and served by Pages, e.g.
    -- '/assets/images/players/smith-sophia.webp'. Players without their own
    -- headshot fall back to the generic silhouette.
    image_path TEXT NOT NULL DEFAULT '/assets/images/players/placeholder-avatar.webp',
    scheduled_date DATE
);
CREATE INDEX idx_bios_date ON player_bios(scheduled_date);

CREATE TABLE user_notification_prefs (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    notify_3day_checkin BOOLEAN DEFAULT TRUE,
    notify_bench_alerts BOOLEAN DEFAULT TRUE,
    daily_bio_scope TEXT DEFAULT 'home_first' -- 'home_first', 'summit_only', 'league_wide'
);
