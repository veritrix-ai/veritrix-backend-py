# GET /v1/metrics/overview

Returns aggregated metrics for the dashboard metrics page.

---

## Request

```
GET /v1/metrics/overview?org_id={org_id}
Authorization: Bearer {clerk_session_token}
```

### Query parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | `string` | Yes | Organization UUID |

---

## Response

**Status:** `200 OK`

[`MetricsOverviewData`](../schemas/metrics-overview.md)

```json
{
  "overview": {
    "total_cost_usd": 0.0,
    "tokens_generated": 0,
    "fail_rate": 0.08,
    "total_events": 150,
    "monthly_spans": 150,
    "monthly_span_limit": 5000
  },
  "span_end_states": [
    { "date": "2026-06-14", "success": 120, "indeterminate": 0, "fail": 10 },
    { "date": "2026-06-15", "success": 18, "indeterminate": 0, "fail": 2 }
  ],
  "span_end_states_distribution": {
    "success": 138,
    "indeterminate": 0,
    "fail": 12
  },
  "spans_per_trace": [
    { "label": "3", "value": 5 },
    { "label": "5", "value": 12 }
  ],
  "trace_duration_distribution": [
    { "label": "2500", "value": 8 },
    { "label": "8400", "value": 3 }
  ]
}
```

---

## Example

```bash
curl "http://localhost:8000/v1/metrics/overview?org_id=11111111-1111-1111-1111-111111111111"
```

---

## Notes

- `overview.total_events` is the total span count for the org.
- `overview.fail_rate` is `error_spans / total_spans`.
- `monthly_spans` counts spans in the current calendar month.
- `monthly_span_limit` is currently a static plan limit (5000).
- Histogram buckets (`spans_per_trace`, `trace_duration_distribution`) are computed from trace-level aggregations.
