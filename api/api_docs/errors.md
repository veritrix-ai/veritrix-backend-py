# Errors

All handled error responses use a consistent JSON shape:

```json
{
  "error": "<human-readable message>"
}
```

Validation errors from FastAPI/Pydantic use the standard `detail` array format.

---

## Status codes

| Status | Meaning | When |
|---|---|---|
| `200 OK` | Success | Valid request with results (may be empty arrays) |
| `401 Unauthorized` | Auth failed | Missing or invalid Clerk session token |
| `403 Forbidden` | Access denied | User cannot access the requested `org_id` |
| `404 Not Found` | Not found | Trace ID does not exist (or not visible to org) |
| `422 Unprocessable Entity` | Validation failed | Invalid query parameters |
| `500 Internal Server Error` | Server error | Unexpected failure |

---

## Common errors

### Unauthorized

**Status:** `401`

```json
{
  "error": "unauthorized"
}
```

**Causes:**
- `Authorization` header missing in production
- Invalid or expired Clerk session token
- `CLERK_JWKS_URL` not configured in non-development environment

---

### Forbidden

**Status:** `403`

```json
{
  "error": "forbidden"
}
```

**Causes:**
- Authenticated user's org does not match the `org_id` query parameter
- User has no org mapping in PostgreSQL

---

### Trace not found

**Status:** `404`

```json
{
  "error": "trace not found"
}
```

**Causes:**
- No spans exist for the given `trace_id`
- Trace belongs to a different org (when org scoping is enforced)

---

### Invalid query parameters

**Status:** `422`

Example — `limit` out of range (max 200):

```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 200",
      "input": "500"
    }
  ]
}
```

---

## Empty results vs errors

An empty trace list is **not** an error:

```json
{
  "traces": [],
  "total": 0,
  "metrics": {
    "total_cost_usd": 0.0,
    "tokens_generated": 0,
    "fail_rate": null,
    "total_events": 0
  }
}
```

This is returned with `200 OK` when the org has no ingested spans yet.
