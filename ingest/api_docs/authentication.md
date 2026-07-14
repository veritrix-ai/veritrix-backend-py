# Authentication

The Ingest API uses **Bearer token authentication** with project API keys issued from the AgentOps web console.

---

## Header format

Every request to protected endpoints must include:

```
Authorization: Bearer {api_key}
```

| Header | Required | Value |
|---|---|---|
| `Authorization` | Yes | `Bearer <api_key>` |
| `Content-Type` | Yes (POST) | `application/json` |

---

## API key format

Development keys follow this pattern:

```
ao_live_<hex>
```

Example (seed data in local docker-compose):

```
ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec
```

---

## Validation flow

1. Extract the token from the `Authorization` header.
2. Reject if the header is missing, malformed, or not a Bearer token.
3. Look up the key in PostgreSQL (`api_keys` table).
4. Reject if the key does not exist or has been revoked (`revoked_at IS NOT NULL`).
5. Resolve the associated `org_id` and attach it to all spans in the batch.

---

## Error response

```json
{
  "error": "invalid api key"
}
```

| Status | Condition |
|---|---|
| `401 Unauthorized` | Missing header, wrong scheme, unknown key, or revoked key |

---

## Security notes

- Never commit API keys to source control.
- Use environment variables (`AGENTOPS_API_KEY`) in agent code and CI.
- Ingest keys are **not** Clerk session tokens — those are used by the App API (port 8000) for dashboard access.
- Rotate keys from the web console if a key is exposed.

---

## Example

```bash
curl -X POST http://localhost:8001/v1/spans \
  -H "Authorization: Bearer ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec" \
  -H "Content-Type: application/json" \
  -d '{"spans": [...]}'
```
