# GET /health

Liveness check. Does not require authentication.

---

## Request

```
GET /health
```

No headers or query parameters required.

---

## Response

**Status:** `200 OK`

```json
{
  "status": "ok"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"ok"` when the service process is running |

---

## Example

```bash
curl http://localhost:8000/health
```

---

## Notes

- Does not verify ClickHouse or PostgreSQL connectivity.
- Use for load balancer health checks and process liveness probes.
