BEGIN;

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

COMMIT;
