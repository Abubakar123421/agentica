# BatchBridge coding context

## Product invariants

- The importer owns the system and operational shipment records.
- A report is a suspicion; only an authorized human can record a safety verdict.
- Product plus manufacturer lot number identifies a batch. Never match on lot number alone.
- Shipment recipients and quantities must come from database records through MCP tools.
- MCP tools are read-only. Agent output is advisory.
- Retailer tasks require importer approval.
- Manufacturer escalation requires the current approved batch proposal and findings from every recipient.
- Triage uses Groq in LLM mode; active traceability/escalation use rules and MCP without model calls.
- Do not reintroduce LLM/API-key dependencies into the two rule-based stages without user direction.
- Customer contact information must not enter MCP output, LLM prompts, or manufacturer packets.
- Every meaningful workflow action must create an audit event.

## Repository layout

- `backend/app/api/`: HTTP routes and role boundaries.
- `backend/app/agents/`: triage, traceability, escalation, and their structured result contracts.
- `backend/app/services/`: workflow, investigation execution, and MCP client.
- `backend/app/mcp_server.py`: read-only evidence tools.
- `backend/app/models.py`: SQLAlchemy domain model.
- `backend/tests/`: integration and security tests.
- `alembic/`: schema migrations.
- `examples/`: synthetic CSV imports.

## Local commands

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
ruff check backend
pytest
uvicorn app.main:app --app-dir backend --reload
```

## Change rules

- Keep database-backed matching deterministic.
- Add schema changes through Alembic.
- Preserve organization scoping when adding endpoints.
- Do not add autonomous recall, dispatch, or verdict behavior.
- Use synthetic data in development and demonstrations.
- Update the relevant Markdown file when product rules, endpoints, architecture, deployment, or demo
  behavior changes.

Read `CONTEXT.md` and `PRODUCT_SPEC.md` before changing behavior. Use `IMPLEMENTATION_PLAN.md` for
remaining work and `DEPLOYMENT.md` for Alternate Clouds requirements.
