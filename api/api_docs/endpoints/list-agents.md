# GET /v1/agents

Returns a health summary for all agents observed in an organization's traces.

---

## Request

```
GET /v1/agents?org_id={org_id}
Authorization: Bearer {clerk_session_token}
```

### Query parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `org_id` | `string` | Yes | Organization UUID |

---

## Response

**Status:** `200 OK`

[`AgentListResponse`](../schemas/agent-list.md)

```json
{
  "agents": [
    {
      "agent_id": "agent-001",
      "agent_name": "Research Analyst",
      "framework": "crewai",
      "total_runs": 42,
      "error_rate": 0.05,
      "avg_duration_ms": 3200,
      "last_seen": "2026-06-15T12:00:00.000Z"
    }
  ]
}
```

---

## Example

```bash
curl "http://localhost:8000/v1/agents?org_id=11111111-1111-1111-1111-111111111111"
```

---

## Notes

- Agents are aggregated from ClickHouse spans grouped by `agent_id`.
- `total_runs` counts distinct `run_id` values per agent.
- `error_rate` is the ratio of error spans to total spans for that agent.
- Results are ordered by `last_seen` descending.
