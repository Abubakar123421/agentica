# BatchBridge

BatchBridge is an importer-owned food batch investigation system. Consumers and retailer food
safety managers report suspected product issues. Three MCP-grounded LangGraph agents triage the
report, trace the exact batch, and prepare manufacturer escalation evidence. Humans approve every
handoff and safety decision.

## Backend quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Open `http://localhost:8000/docs`. Demo data is seeded by default. Accounts use the password in
`DEMO_PASSWORD`:

- `importer@batchbridge.demo`
- `retailer-a@batchbridge.demo`
- `retailer-b@batchbridge.demo`
- `retailer-c@batchbridge.demo`
- `manufacturer@batchbridge.demo`

Set `GROQ_API_KEY` in the ignored `.env`, with `AGENT_MODE=llm` (the default). Each agent uses Groq
to select and call read-only MCP tools, inspect results, and submit a validated proposal for human
review. Restart the backend after changing environment variables. Never put keys in `.env.example`.
`AGENT_MODE=demo` explicitly selects the older rule-based simulation for offline tests. An LLM-mode
failure is displayed as a failed run; it never silently switches to demo logic.

## Frontend quick start

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`. The production Docker image builds the
responsive React application and serves it from the FastAPI origin.

## Verification

```bash
ruff check backend
pytest
```

## Alternate Clouds

Create a PostgreSQL 17 template service and a GitHub application service. Link PostgreSQL to the
application so `DATABASE_URL` is injected. Set the other values from `.env.example`, then follow the
required order: **set variables, rebuild, deploy**.

The container listens on `0.0.0.0:$PORT`. All durable state is stored in PostgreSQL.

## Backend behavior

- Consumers submit reports directly and receive a private tracking token.
- Retailer safety managers can file their own report, review and forward customer cases, add
  evidence, and complete assigned checks.
- Triage, traceability, and escalation agents share one read-only MCP evidence server with explicit
  per-agent tool permissions.
- Groq chooses investigation tool calls and recommendations. Canonical shipment recipients,
  quantities, product and lot IDs are hydrated from MCP responses and validated before review.
- Agent cards show execution mode, model, model-turn count, evidence summaries, questions, and MCP
  calls. Earlier saved runs are labeled as previous demo runs; rerun them to obtain a Groq proposal.
- Importer approval creates retailer tasks; no tool or model can create them before that approval.
- Manufacturer escalation requires an approved traceability proposal, at least one human retailer
  finding, an escalation-agent packet, and a second importer approval.

The interactive OpenAPI contract at `/docs` covers the full API.

## Project documentation

- [`AGENTS.md`](AGENTS.md): project invariants and coding handoff for future agents.
- [`CONTEXT.md`](CONTEXT.md): stable decisions, roles, safety rules, and demo dataset.
- [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md): complete use case, scope, requirements, and success criteria.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): components, trust boundaries, data flow, and deployment shape.
- [`API_REFERENCE.md`](API_REFERENCE.md): endpoint and MCP tool map.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): checklist from product scope through submission.
- [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md): judge-ready story, checks, and fallback path.
- [`FRONTEND_REFERENCE.md`](FRONTEND_REFERENCE.md): responsive UI direction.
- [`DEPLOYMENT.md`](DEPLOYMENT.md): Alternate Clouds setup and verification.

