# GET /v1/traces

List traces for an organization, with optional filtering and pagination.

---

## Request

```
GET /v1/traces?org_id={org_id}&limit={limit}&offset={offset}&status={status}
Authorization: Bearer {clerk_session_token}
```

### Query parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `org_id` | `string` | Yes | — | Organization UUID |
| `limit` | `integer` | No | `50` | Page size (1–200) |
| `offset` | `integer` | No | `0` | Pagination offset |
| `status` | `string` | No | — | Filter by `"ok"` or `"error"` |

A trace is marked `"error"` if any span in the trace has `status = "error"`.

---

## Response

**Status:** `200 OK`

[`TraceListResponse`](../schemas/trace-list.md)

```json
{
  "traces": [
    {
      "trace_id": "abc123",
      "run_id": "abc123",
      "agent_name": "Research Analyst",
      "name": "Research Analyst",
      "status": "ok",
      "duration_ms": 2500,
      "span_count": 5,
      "start_time": "2026-06-15T12:00:00.000Z",
      "tags": [],
      "cost_usd": null,
      "error_count": 0
    }
  ],
  "total": 1,
  "metrics": {
    "total_cost_usd": 0.0,
    "tokens_generated": 0,
    "fail_rate": 0.0,
    "total_events": 5
  }
}
```

---

## Example

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111&limit=20&status=ok"
```

Filter errors only:

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111&status=error"
```

---

## Notes

- Traces are aggregated from ClickHouse spans grouped by `trace_id` and `run_id`.
- Results are ordered by `start_time` descending (most recent first).
- `metrics` reflects org-wide totals, not just the current page.
