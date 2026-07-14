# Errors

All error responses use a consistent JSON shape:

```json
{
  "error": "<human-readable message>"
}
```

---

## Status codes

| Status | Meaning | When |
|---|---|---|
| `202 Accepted` | Batch queued for insert | Valid request, within rate limit |
| `400 Bad Request` | Validation failed | Invalid span attributes, empty batch, or business rule violation |
| `401 Unauthorized` | Authentication failed | Missing, malformed, or invalid API key |
| `422 Unprocessable Entity` | Schema validation failed | Malformed JSON body or Pydantic field errors |
| `429 Too Many Requests` | Rate limited | Organization exceeded requests-per-minute quota |
| `500 Internal Server Error` | Server error | Unexpected failure (non-development environments) |

---

## Common errors

### Invalid API key

**Status:** `401`

```json
{
  "error": "invalid api key"
}
```

**Causes:**
- `Authorization` header missing
- Scheme is not `Bearer`
- Key not found in database
- Key has been revoked

---

### Rate limited

**Status:** `429`

```json
{
  "error": "rate limited"
}
```

**Causes:**
- Organization exceeded `INGEST_RATE_LIMIT_PER_MINUTE` (default: 1000 requests/minute)

**Resolution:** Back off and retry. The SDK handles retries automatically with exponential backoff.

---

### Missing required attributes

**Status:** `422` (Pydantic validation)

Returned when a span's `attributes` object is missing required AgentOps keys:

```
agentops.agent_id
agentops.agent_name
agentops.run_id
agentops.framework
agentops.span_type
```

Example validation detail (FastAPI default format):

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "spans", 0, "attributes"],
      "msg": "Value error, missing required attributes: agentops.run_id, agentops.framework",
      "input": {}
    }
  ]
}
```

---

### Empty batch

**Status:** `422`

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "spans"],
      "msg": "Value error, batch must contain at least one span"
    }
  ]
}
```

---

### Batch too large

**Status:** `422`

Maximum **500 spans** per request.

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "spans"],
      "msg": "Value error, batch exceeds maximum of 500 spans"
    }
  ]
}
```

---

## Client retry guidance

| Status | Retry? | Notes |
|---|---|---|
| `202` | No | Success |
| `400` | No | Fix payload |
| `401` | No | Fix API key |
| `422` | No | Fix schema |
| `429` | Yes | Back off exponentially |
| `5xx` | Yes | Back off exponentially |

The AgentOps SDK implements this retry policy automatically and fails open (never crashes the user's agent).
