# Authentication

The App API uses **Clerk session token authentication** for dashboard users. This is different from the Ingest API, which uses project API keys.

---

## Header format

Protected routes expect:

```
Authorization: Bearer {clerk_session_token}
```

| Header | Required | Value |
|---|---|---|
| `Authorization` | Yes (production) | `Bearer <clerk_session_token>` |

The session token is obtained from Clerk on the frontend via `auth().getToken()` and forwarded by `frontend/lib/api.ts`.

---

## Organization scoping

List endpoints require an `org_id` query parameter:

```
GET /v1/traces?org_id=11111111-1111-1111-1111-111111111111
GET /v1/agents?org_id=11111111-1111-1111-1111-111111111111
GET /v1/metrics/overview?org_id=11111111-1111-1111-1111-111111111111
```

In production, the authenticated user's organization must match the requested `org_id`. Requests for a different org return `403 Forbidden`.

Trace detail endpoints (`GET /v1/traces/{trace_id}`) do not require `org_id` in the URL — org access is enforced from the Clerk token when auth is enabled.

---

## Validation flow

1. Extract Bearer token from the `Authorization` header.
2. Verify JWT signature against Clerk JWKS (`CLERK_JWKS_URL`).
3. Extract `sub` (user ID) and optional `org_id` from the token payload.
4. If `org_id` is absent, look up the user's org via PostgreSQL (`users.clerk_user_id`).
5. For list routes, compare resolved org against the `org_id` query parameter.

---

## Environment variables

| Variable | Description |
|---|---|
| `CLERK_SECRET_KEY` | Clerk secret key (backend) |
| `CLERK_JWKS_URL` | JWKS endpoint, e.g. `https://your-app.clerk.accounts.dev/.well-known/jwks.json` |

---

## Local development bypass

When `ENVIRONMENT=development` and `CLERK_JWKS_URL` is **not set**:

- Requests are accepted **without** an `Authorization` header.
- The `org_id` query parameter is trusted directly.
- Trace detail lookups are not org-scoped (any `trace_id` is accessible).

Use the demo org from seed data for local testing:

```
11111111-1111-1111-1111-111111111111
```

---

## Error responses

### Unauthorized

**Status:** `401`

```json
{
  "error": "unauthorized"
}
```

Missing header, invalid token, or expired session.

### Forbidden

**Status:** `403`

```json
{
  "error": "forbidden"
}
```

Authenticated user does not have access to the requested `org_id`.

---

## Example (production)

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..."
```

## Example (local dev, no Clerk)

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
```
