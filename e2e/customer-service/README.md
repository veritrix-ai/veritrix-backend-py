# Customer service E2E test (OpenAI Agents)

Airline customer service **multi-agent** demo adapted from Google Colab. Uses the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) with triage, FAQ, and seat-booking agents.

## What it tests

- Real LLM agent run with tool calls and handoffs
- `agentops.init()` + per-turn `agentops.trace()` wrapping
- Full pipeline: SDK → Ingest → ClickHouse → App API

## Prerequisites

```bash
python3 -m pip install openai-agents python-dotenv
export OPENAI_API_KEY=your_openai_api_key_here
```

Optional: copy `backend/e2e/.env.example` to `backend/e2e/.env` and set keys there.

## Scripts

| Script | Purpose |
|---|---|
| [`run.sh`](./run.sh) | Run agent (`--demo` by default) |
| [`run-interactive.sh`](./run-interactive.sh) | Interactive chat mode |
| [`validate.sh`](./validate.sh) | Health → demo agent → curl verification |
| [`agent.py`](./agent.py) | Python agent |

## Quick start

**Scripted demo (recommended):**

```bash
cd backend/e2e/customer-service
chmod +x run.sh validate.sh run-interactive.sh
./validate.sh
```

**Agent only:**

```bash
./run.sh              # demo mode (2 scripted messages)
./run-interactive.sh  # type messages, quit with 'quit'
```

## Demo messages (`--demo`)

1. "What is the baggage allowance for my flight?" → FAQ / triage handoff
2. "I want to change my seat to 12A..." → seat booking agent + tool

## Environment variables

| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | Yes | — |
| `AGENTOPS_API_KEY` | No | seed dev key |
| `AGENTOPS_ENDPOINT` | No | `http://localhost:8001` |

## Verify traces

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
curl "http://localhost:8000/v1/traces/<TRACE_ID>"
```

Look for tags: `customer-service-agent`, `openai-agents`, `agentops-example`.

## Origin

Adapted from the AgentOps Google Colab notebook (airline customer service with OpenAI Agents SDK).
