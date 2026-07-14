# AgentListResponse

Response for `GET /v1/agents`.

---

## Shape

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

## AgentSummary fields

| Field | Type | Description |
|---|---|---|
| `agent_id` | `string` | Unique agent instance ID |
| `agent_name` | `string` | Human-readable name |
| `framework` | `string` | `"langchain"`, `"crewai"`, `"manual"`, or `"openai"` |
| `total_runs` | `integer` | Distinct run count |
| `error_rate` | `float` | Ratio of error spans (0.0–1.0) |
| `avg_duration_ms` | `integer` | Average span duration |
| `last_seen` | `string` | Most recent activity (ISO 8601) |
