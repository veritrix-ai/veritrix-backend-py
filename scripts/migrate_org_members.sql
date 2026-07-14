-- Apply org members / invites tables to an existing AgentOps Postgres database.
-- Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    clerk_user_id TEXT,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, email)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON org_members(org_id);

CREATE TABLE IF NOT EXISTS org_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'viewer')),
    invited_by TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
    token TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(24), 'hex'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '14 days')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_org_invites_pending_email
    ON org_invites(org_id, lower(email))
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_org_invites_org_id ON org_invites(org_id);

INSERT INTO org_members (org_id, user_id, clerk_user_id, email, role)
SELECT u.org_id, u.id, u.clerk_user_id, u.email, 'owner'
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = u.org_id AND lower(m.email) = lower(u.email)
);
