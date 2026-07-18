BEGIN;

ALTER TABLE orgs
    ADD COLUMN IF NOT EXISTS clerk_org_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orgs_clerk_org_id
    ON orgs(clerk_org_id)
    WHERE clerk_org_id IS NOT NULL;

COMMIT;
