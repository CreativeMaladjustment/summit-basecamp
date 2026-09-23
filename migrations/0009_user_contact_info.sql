-- Summit Basecamp — phone and a fallback contact email for a member's
-- Settings "Group & profile" card, backing PATCH /api/me. Deliberately
-- separate from `email` (the sign-in identity Google/Apple hand back,
-- unique per migration 0001) -- a member may want a different number or
-- address reachable for critical ticket transfers than the one their
-- Google or Apple account uses.
ALTER TABLE users ADD COLUMN phone TEXT;
ALTER TABLE users ADD COLUMN contact_email TEXT;
