# BatchBridge product context

## Purpose

BatchBridge helps a country importer investigate suspected food contamination across fragmented
retailer records. It does not diagnose contamination or trigger recalls automatically.

## Ownership and roles

- The importer owns the system, product catalogue, received batches, and distribution records.
- A customer can submit a complaint directly through the public importer portal.
- A retailer food safety manager can submit an inspection finding or add evidence to a case.
- A retailer food safety manager can review a customer case and explicitly forward it to the
  importer with notes. Direct customer reports remain visible to the importer before this review.
- Importer investigators approve retailer checks and manufacturer escalations.
- The overseas manufacturer reviews the evidence packet and responds in the portal.
- "Retailer food safety manager" means internal retailer staff. It is distinct from a government
  food safety officer.

## Core workflow

`New report -> Triage -> Retailer/importer review -> Traceability -> Retailer checks -> Escalation -> Manufacturer review -> Importer verdict -> Closed`

`Waiting for information` is a temporary case state. A report is suspicion, not proof. The agent may
recommend a batch match and draft handoffs, but a human decides whether to send them. A negative
visual inspection never clears an entire batch. Urgent escalation does not wait for every retailer.

### Agent responsibilities and approval gates

1. **Triage Agent:** runs when a customer or retailer report is created, reads the case, product
   candidates, and related reports, then recommends forwarding, requesting information, or review.
   A retailer may review and forward the report; otherwise an importer investigator reviews the
   triage proposal before traceability can start.
2. **Traceability Agent:** runs after retailer forwarding or approved triage. It resolves product
   plus manufacturer lot against importer records and proposes retailer checks from exact shipment
   records. An importer investigator approves the proposal before checks are assigned.
3. **Escalation Agent:** runs after the traceability proposal is approved and at least one retailer
   submits a human finding. It prepares an evidence packet and flags missing or conflicting
   information. The importer separately approves sending the packet to the manufacturer.
4. **Manufacturer and importer:** a manufacturer reviewer submits the company response. The importer
   investigator records the final human verdict and closes the case.

Each agent is a separately queued LangGraph run, writes a typed proposal, and pauses at a human
interrupt. The API and database enforce the gates; resuming a graph is not the source of truth for
an approval. A retailer can create an inspection report or review a customer report, and customer
reports can also enter the importer queue directly.

## Data rules

- A batch is identified by product plus manufacturer lot number. A number such as `38` is not
  globally unique.
- Recipient retailers and quantities always come from shipment records, never from the LLM.
- Every state transition, approval, and response is append-only in the audit timeline.
- Public tracking uses a random token. Customer contact details are excluded from agent prompts and
  manufacturer packets.

## Technical decisions

- API: Python 3.12, FastAPI, SQLAlchemy, Alembic.
- Workflow: three separately invoked bounded LangGraph agents for triage, traceability, and
  escalation, each ending at an explicit human interrupt and persisted proposal.
- Model: Groq `openai/gpt-oss-20b`, configurable with `GROQ_MODEL`.
- Tools: one real MCP stdio server with read-only case, product, batch, shipment, report, evidence,
  timeline, distribution, and inspection lookups. Each agent has a strict tool allowlist; approvals
  and mutations stay in authenticated API handlers.
- Database: PostgreSQL 17 on Alternate Clouds; SQLite is supported for local development and tests.
- Authentication: seeded password-protected staff accounts, server-side sessions, fixed roles and
  organizations, no public signup.
- Notifications: in-app inboxes only.
- Frontend target: responsive React, TypeScript, Vite, and Tailwind served from the same application
  origin in production.
- Production image: Docker builds the frontend with Node, copies its static assets into the Python
  image, runs Alembic migrations, then starts FastAPI/Uvicorn on the platform-provided port.

## Demo dataset

Fictional product `CHOC-100`, manufacturer lot `38`: 10,000 received; 3,000 sent to Retailer A,
2,000 to Retailer B, 1,000 to Retailer C, and 4,000 retained by the importer. Retailer D only receives
lot `39` and must never appear in lot `38` results.

## Deferred after the hackathon

Government integrations, live retailer ERP connectors, OCR, email/SMS notifications, automated
recalls, multi-importer tenancy, and n8n automation.

