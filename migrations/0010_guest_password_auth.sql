-- Six shared-password login slots for the landing screen (replaces the
-- unimplemented Google/Apple OIDC sign-in -- see src/auth.py and
-- src/handlers.begin_session). Every slot starts as "Guest N"; PATCH /api/me
-- lets whoever is signed into a slot replace that with their own name, which
-- sticks for that slot going forward.
INSERT INTO users (id, email, name, auth_provider, auth_provider_id, created_at)
VALUES
    ('usr_guest1', 'guest1@summit-basecamp.local', 'Guest 1', 'password', 'guest1', CURRENT_TIMESTAMP),
    ('usr_guest2', 'guest2@summit-basecamp.local', 'Guest 2', 'password', 'guest2', CURRENT_TIMESTAMP),
    ('usr_guest3', 'guest3@summit-basecamp.local', 'Guest 3', 'password', 'guest3', CURRENT_TIMESTAMP),
    ('usr_guest4', 'guest4@summit-basecamp.local', 'Guest 4', 'password', 'guest4', CURRENT_TIMESTAMP),
    ('usr_guest5', 'guest5@summit-basecamp.local', 'Guest 5', 'password', 'guest5', CURRENT_TIMESTAMP),
    ('usr_guest6', 'guest6@summit-basecamp.local', 'Guest 6', 'password', 'guest6', CURRENT_TIMESTAMP);
