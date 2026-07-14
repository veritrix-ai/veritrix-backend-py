# Manual E2E test

Minimal test agent with **no OpenAI dependency**. Sends nested manual spans (agent → tool → llm) through the SDK to validate ingest and storage.

## What it tests

- `agentops.init()` / `agentops.trace()` / `agentops.end()`
- Ingest API key validation (Postgres)
- ClickHouse span insert
- App API trace list, detail, graph, agents

## Scripts

| Script | Purpose |
|---|---|
| [`run.sh`](./run.sh) | Run the agent only (prints curl commands) |
| [`validate.sh`](./validate.sh) | Health checks → run agent → curl verification |
| [`agent.py`](./agent.py) | Python test agent |

## Quick start

```bash
cd backend/e2e/manual
chmod +x run.sh validate.sh
./validate.sh
```

Agent only:

```bash
./run.sh
```

## Manual verification

After `./run.sh`, note the printed `trace_id`:

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
curl "http://localhost:8000/v1/traces/<TRACE_ID>"
curl "http://localhost:8000/v1/traces/<TRACE_ID>/graph"
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AGENTOPS_API_KEY` | seed key | Ingest API key |
| `AGENTOPS_ENDPOINT` | `http://localhost:8001` | Ingest base URL |

## Expected spans

| Span name | Type |
|---|---|
| `session` | agent (root, auto-created by init) |
| `research-step` | agent |
| `web-search` | tool (child) |
| `summarize` | llm (child) |
