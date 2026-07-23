# AgentOps Ingest API — Documentation

The Ingest API receives OpenTelemetry-compatible spans from the AgentOps Python SDK and stores them in ClickHouse. It is a write-only, latency-sensitive service — separate from the App API that serves the dashboard.

| | |
|---|---|
| **Base URL (local)** | `http://localhost:8001` |
| **Port** | `8001` |
| **Protocol** | HTTPS in production; HTTP for local development |
| **Content type** | `application/json` |
| **OpenAPI spec** | [`openapi.yaml`](./openapi.yaml) |
| **Interactive docs** | `http://localhost:8001/docs` (Swagger UI, when server is running) |
| **ReDoc** | `http://localhost:8001/redoc` (when server is running) |

---

## Documentation index

| Document | Description |
|---|---|
| [Authentication](./authentication.md) | API key format, headers, validation |
| [Endpoints](./endpoints/README.md) | All HTTP routes |
| [Schemas](./schemas/README.md) | Request and response body shapes |
| [Errors](./errors.md) | Status codes and error payloads |
| [OpenAPI](./openapi.yaml) | Machine-readable API specification |

---

## Quick start

### 1. Start the service

```bash
cd backend
docker compose up -d
cp shared/.env.example shared/.env
PYTHONPATH=. uvicorn ingest.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Send spans

```bash
curl -X POST http://localhost:8001/v1/spans \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "spans": [
    {
      "trace_id": "abc123",
      "span_id": "span-001",
      "name": "research-agent",
      "start_time": "2026-06-15T12:00:00.000Z",
      "end_time": "2026-06-15T12:00:02.500Z",
      "status": "ok",
      "attributes": {
        "agentops.agent_id": "agent-001",
        "agentops.agent_name": "Research Analyst",
        "agentops.run_id": "abc123",
        "agentops.framework": "crewai",
        "agentops.span_type": "agent",
        "agentops.duration_ms": 2500
      },
      "input_preview": "Analyze job market for ML engineers",
      "output_preview": "Found 3 trending roles..."
    }
  ]
}
EOF
```

### 3. Expected response

```json
{
  "accepted": 1
}
```

A `202 Accepted` means the batch passed validation and was queued for async insert into ClickHouse. It does **not** guarantee durable storage yet — the SDK retries on failure.

---

## SDK integration

Users do not call this API directly in normal usage. The Python SDK handles batching, retries, and fail-open behavior:

```python
import veritrix

veritrix.init(api_key="YOUR_API_KEY", default_tags=["crewai"])
# spans are sent automatically to POST /v1/spans
veritrix.end()
```

Default ingest endpoint: `http://localhost:8001/v1/spans`  
Override with the `VERITRIX_ENDPOINT` (or legacy `AGENTOPS_ENDPOINT`) environment variable or SDK `endpoint` parameter.

---

## Architecture notes

- Spans are validated synchronously; ClickHouse inserts run in a **background task** after the `202` response.
- API keys are validated against PostgreSQL (`api_keys` table). The resolved `org_id` is attached to every stored span.
- Rate limiting is applied **per organization** (default: 1000 requests/minute, configurable via `INGEST_RATE_LIMIT_PER_MINUTE`).
- Maximum batch size: **500 spans** per request.

---

## Related

- [Backend README](../../README.md) — local development setup
- [AGENTS.md](../../../AGENTS.md) — full platform architecture
