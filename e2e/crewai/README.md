# CrewAI E2E test

Minimal **two-agent sequential crew** to validate the AgentOps CrewAI integration (`setup_crewai()` step callback patch).

## What it tests

- `agentops.init(framework="crewai")` auto-instruments `Crew.__init__`
- Per-step spans from CrewAI `step_callback` (agent role names as span names)
- `framework=crewai` on spans through ingest → ClickHouse → App API

## Prerequisites

```bash
python3 -m pip install "crewai>=0.28.0" python-dotenv
export OPENAI_API_KEY=your_openai_api_key_here
```

Optional: `cp ../.env.example ../.env` and set keys there.

Uses `gpt-4o-mini` by default (`OPENAI_MODEL_NAME`).

## Scripts

| Script | Purpose |
|---|---|
| [`run.sh`](./run.sh) | Run the crew |
| [`validate.sh`](./validate.sh) | Health → crew → curl verification |
| [`agent.py`](./agent.py) | Python crew |

## Quick start

```bash
cd backend/e2e/crewai
chmod +x run.sh validate.sh
./validate.sh
```

Agent only:

```bash
./run.sh
./run.sh --topic "multi-agent tracing"
```

## Crew layout

| Agent | Role |
|---|---|
| Research Analyst | 3 bullet points on `{topic}` |
| Content Writer | One-sentence summary |

Process: `Process.sequential` (research → summary).

## Environment variables

| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | Yes | — |
| `OPENAI_MODEL_NAME` | No | `gpt-4o-mini` |
| `AGENTOPS_API_KEY` | No | seed dev key |
| `AGENTOPS_ENDPOINT` | No | `http://localhost:8001` |

## Expected traces

After `./validate.sh`, the latest trace should include:

- Root `session` span (`framework=crewai`)
- Child spans named **Research Analyst** and **Content Writer**
- Tags: `e2e-test`, `crewai`

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
curl "http://localhost:8000/v1/traces/<TRACE_ID>"
```

## Troubleshooting

- **`ImportError: crewai`** — `pip install "crewai>=0.28.0"`
- **No step spans** — confirm `agentops.init()` runs *before* `Crew(...)` is constructed
- **401 on ingest** — check `AGENTOPS_API_KEY` matches Postgres seed data
- **Backend APIs crash after installing crewai** — crewai can upgrade Starlette and break FastAPI. Use a separate venv for E2E agents, or reinstall backend deps: `pip install "starlette>=0.40.0,<0.48.0"`
