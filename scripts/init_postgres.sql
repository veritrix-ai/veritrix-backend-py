CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    clerk_org_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    clerk_user_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS onboarding_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    usage TEXT NOT NULL CHECK (usage IN ('hobby', 'work', 'help')),
    company_size TEXT NOT NULL,
    building_description TEXT NOT NULL,
    stage TEXT NOT NULL,
    heard_from TEXT NOT NULL,
    frameworks TEXT[] NOT NULL DEFAULT '{}',
    providers TEXT[] NOT NULL DEFAULT '{}',
    help_goals TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_profiles_org_id
    ON onboarding_profiles(org_id);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    project_id UUID REFERENCES projects(id),
    key_value TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT 'default',
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_value ON api_keys(key_value) WHERE revoked_at IS NULL;

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

INSERT INTO orgs (id, name)
VALUES ('11111111-1111-1111-1111-111111111111', 'Demo Org')
ON CONFLICT (id) DO NOTHING;

INSERT INTO projects (id, org_id, name)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Default Project'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO api_keys (org_id, project_id, key_value, name)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    'ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec',
    'Development Key'
)
ON CONFLICT (key_value) DO NOTHING;

-- Backfill owners for any users missing an org_members row.
INSERT INTO org_members (org_id, user_id, clerk_user_id, email, role)
SELECT u.org_id, u.id, u.clerk_user_id, u.email, 'owner'
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM org_members m
    WHERE m.org_id = u.org_id AND lower(m.email) = lower(u.email)
);
