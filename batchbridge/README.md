# BatchBridge

BatchBridge is an importer-owned food batch investigation system. Consumers and retailer food
safety managers report suspected product issues. An MCP-grounded LangGraph workflow traces the
batch through importer shipment records and drafts retailer inspection tasks. Humans approve every
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
- The LangGraph workflow calls the read-only MCP evidence server for case, product, batch,
  distribution, related report, and inspection facts.
- Groq adds a bounded risk summary and follow-up questions when configured. The database remains the
  source of truth if Groq is unavailable.
- Importer approval creates retailer tasks; no tool or model can create them before that approval.
- Manufacturer escalation requires an approved batch proposal and at least one human retailer
  finding. The importer makes the final case decision.

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

