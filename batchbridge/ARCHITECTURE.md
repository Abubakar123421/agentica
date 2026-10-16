# BatchBridge architecture

## System overview

```mermaid
flowchart LR
    C[Customer portal] --> API[FastAPI application]
    R[Retailer portal] --> API
    I[Importer portal] --> API
    M[Manufacturer portal] --> API
    API --> DB[(PostgreSQL)]
    API --> T[Triage agent]
    API --> TR[Traceability agent]
    API --> E[Escalation agent]
    T --> MCP[MCP evidence server]
    TR --> MCP
    E --> MCP
    MCP --> DB
    T --> G[Groq API]
```

The importer owns the application and source data. FastAPI is the authorization and mutation
boundary. LangGraph runs LLM triage and two rule-based stages with human gates between stages. The shared MCP server
exposes read-only evidence tools with per-agent allowlists, and PostgreSQL remains the source of
truth.

## Components

| Component | Location | Responsibility |
| --- | --- | --- |
| API application | `backend/app/main.py` | HTTP entry point, routing, CORS, startup recovery |
| Route modules | `backend/app/api/` | Authentication, reports, cases, imports, evidence, inspections, escalations |
| Domain models | `backend/app/models.py` | Persistent entities and constraints |
| Investigation service | `backend/app/services/investigation.py` | Executes and stores background investigation runs |
| Agents | `backend/app/agents/` | Triage, exact-batch traceability, escalation packet, structured outputs |
| Workflow | `backend/app/services/workflow.py` | Routes one bounded agent run to an explicit human interrupt |
| MCP client | `backend/app/services/mcp_client.py` | Calls the local MCP evidence tools |
| MCP server | `backend/app/mcp_server.py` | Read-only case, product, batch, shipment, related report, and finding tools |
| Audit service | `backend/app/audit.py` | Append-only case events |
| Migrations | `alembic/` | PostgreSQL and SQLite compatible schema history |

## Trust boundaries

- Public users can create and privately track reports; the tracking token is stored as a hash.
- Staff use server-side sessions with fixed roles and organizations.
- Retailers can access cases and inspections belonging to their organization.
- Manufacturers can access escalations addressed to their organization.
- Only importer investigators can run analysis, approve proposals, import operational records, and
  close cases.
- MCP tools cannot modify records.
- LLM output is advisory and cannot create tasks, escalate a case, or set a safety verdict.

## Investigation sequence

```mermaid
sequenceDiagram
    participant U as Customer or retailer
    participant A as API
    participant R as Retailer safety manager
    participant H as Importer investigator
    participant T as Triage Agent
    participant X as Traceability Agent
    participant E as Escalation Agent
    participant Q as MCP tools
    participant D as PostgreSQL

    U->>A: Submit suspected issue
    A->>D: Store case and audit event
    R->>A: Review photo and preview simulated barcode match
    A->>D: Check product/lot and supermarket shipment
    R->>A: Confirm identity and forward photo case
    A->>D: Save verified identity and officer audit event
    A->>T: Queue triage run
    T->>Q: Read case, product candidates, related reports
    Q->>D: Query approved operational records
    D-->>Q: Structured evidence
    Q-->>T: Evidence and tool trace
    T-->>D: Save triage proposal and run
    H->>A: Approve current triage proposal
    A->>X: Queue rule-based traceability after gate
    X->>Q: Read batch and distribution records
    Q->>D: Query exact product/lot shipment data
    D-->>X: Batch recipients and quantities
    X-->>D: Save inspection proposal
    H->>A: Approve retailer checks
    A->>D: Create retailer tasks and audit event
    R->>A: Every assigned retailer submits a human inspection finding
    H->>A: Start escalation analysis
    A->>E: Queue rule-based escalation run
    E->>Q: Read approved trace, findings, evidence, timeline
    E-->>D: Save manufacturer packet proposal
    H->>A: Approve packet delivery
    A->>D: Create escalation and audit event
```

The diagram shows the photo-report path. The officer confirms a fictional barcode fixture, not a
decoded image or a contamination diagnosis. Photo reports cannot proceed to importer traceability
until this officer forwarding step. Legacy structured reports retain creation-time triage and can
proceed after explicit approval of the latest triage proposal. A customer report is visible to the
importer immediately. Escalation analysis requires completed findings from all assigned retailers.
The importer reviews the rule-based escalation recommendation before follow-up checks, monitoring, or manufacturer dispatch.

## Core data relationships

- An organization is an importer, retailer, or manufacturer.
- A user belongs to one organization and has one role.
- A product belongs to a manufacturer and can have many aliases.
- A batch belongs to one product; product plus batch number is unique.
- A shipment connects one batch to one retailer.
- A case contains the reported issue and may reference a retailer and batch number.
- Evidence, agent runs, proposals, approvals, retailer reviews, inspections, escalations, and audit
  events belong to a case.

See the Alembic migration for the executable schema and `/docs` for the generated request and
response contract.

## Reliability behavior

- Queued or interrupted agent runs are recovered on application startup.
- In default LLM mode, triage runs a bounded Groq tool-calling loop within its LangGraph node.
  Tool schemas come from MCP discovery and are filtered by the stage's allowlist. Model decisions
  are validated against a ledger of successful MCP responses before a proposal can reach review.
- Traceability and escalation execute fixed MCP lookups and data-driven rules without Groq.
- Triage failures never silently fall back. Offline triage simulation requires explicit
  `AGENT_MODE=demo`. Pending results from changed execution modes can be superseded; history remains.
- Approval and import requests support idempotent behavior where duplicate actions would be risky.
- Health endpoints separate process liveness from database readiness.
- PostgreSQL stores all durable production state; local SQLite exists for development and tests.

## Deployment topology

The intended deployment connects the GitHub repository to an Alternate Clouds application service with
`batchbridge` as its root directory. A PostgreSQL 17 template service is linked as `DB`, which
provides `DATABASE_URL`. The container runs database migrations before starting Uvicorn and listens
on `0.0.0.0:$PORT`.

## Hybrid execution update (2026-10-17)

Only triage uses Groq (`GROQ_TRIAGE_API_KEY`, falling back to `GROQ_API_KEY`).
Traceability and escalation always use deterministic rules and read-only MCP records,
regardless of AGENT_MODE; their dedicated API-key slots were removed. Traceability
requires an exact SKU/name/known alias plus lot and recorded shipments. Escalation
requires every assigned retailer finding; observed issues prepare a manufacturer
packet, inconclusive findings without observed issues propose targeted follow-up,
and otherwise propose monitoring. Every consequential action still requires human
approval. These stages are labeled rule-based in the UI, not LLM-powered.
Existing pending results from another execution mode can be rerun; history remains.
