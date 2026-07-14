# GET /health

Liveness check. Does not require authentication.

---

## Request

```
GET /health
```

No headers or body required.

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
curl http://localhost:8001/health
```

```json
{
  "status": "ok"
}
```

---

## Notes

- This endpoint does **not** verify ClickHouse or PostgreSQL connectivity.
- Use it for load balancer health checks and process liveness probes.
