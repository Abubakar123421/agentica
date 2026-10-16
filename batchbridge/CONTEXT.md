# BatchBridge product context

## Purpose

BatchBridge helps a country importer investigate suspected food contamination across fragmented
retailer records. It does not diagnose contamination or trigger recalls automatically.

## Ownership and roles

- The importer owns the system, product catalogue, received batches, and distribution records.
- A customer selects a supermarket, describes the issue, and submits 1–3 packaging/problem photos
  through the public importer portal. Customers do not enter product codes or lot numbers.
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
visual inspection never clears an entire batch. The normal workflow waits for findings from every assigned retailer; no emergency bypass is implemented.

### Agent responsibilities and approval gates

1. **Triage Agent:** for photo reports, runs after the supermarket officer verifies and forwards the
   case. Legacy structured reports and retailer reports still run triage on creation. It reads the case, product
   candidates, and related reports, then recommends forwarding, requesting information, or review.
   A retailer may review and forward the report; an importer investigator must separately approve the latest
   triage proposal before traceability can start.
2. **Traceability Agent:** runs after explicit approval of the latest triage proposal. It resolves product
   plus manufacturer lot against importer records and proposes retailer checks from exact shipment
   records. An importer investigator approves the proposal before checks are assigned.
3. **Escalation Agent:** runs after the traceability proposal is approved and every assigned retailer
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
- Agent mode: `AGENT_MODE=llm` by default. Groq chooses MCP tool calls, evaluates returned evidence,
  and produces the recommendation, confidence, rationale, summary and follow-up questions. The
  application validates the final proposal against the actual tool responses. It never accepts
  invented product/lot IDs or model-written retailer lists. Groq failures remain explicit failures;
  `AGENT_MODE=demo` is an explicitly chosen offline simulation used by regression tests.
- Each run allows up to 16 model turns and 30 MCP calls, with an overall 180-second timeout and
  bounded rate-limit retries. A read-only evidence ledger scopes case IDs and binds batch tools to
  retrieved products and the case's lot. Only the API can apply human-approved mutations.
- Secrets belong in ignored `.env`; `.env.example` must stay blank for `GROQ_API_KEY`.
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

Photo reports use `source=customer_photo` and start with an unidentified product. A supermarket
officer previews the simulated barcode lookup, checks the photos, and confirms forwarding. The
server resolves the product and lot again, checks a matching shipment to that supermarket, saves
`demo_barcode_verified` in the audit timeline, and starts triage. Importer traceability cannot bypass
this officer handoff. This verifies product identity only; the safety verdict remains unconfirmed.

The customer form includes **Try with a demo photo**, which creates fictional packaging with the
code `DEMO-CHOC-38`. The lookup maps this code to `CHOC-100` lot `38`; `DEMO-CHOC-39` maps to lot `39`.
These are explicit demo fixtures, with no image decoding, real barcode scanning, or OCR. Photos
are stored atomically with the report in the existing evidence table (JPEG/PNG, max 5 MB each).

Fictional product `CHOC-100`, manufacturer lot `38`: 10,000 received; 3,000 sent to Retailer A,
2,000 to Retailer B, 1,000 to Retailer C, and 4,000 retained by the importer. Retailer D only receives
lot `39` and must never appear in lot `38` results.

## Deferred after the hackathon

Government integrations, live retailer ERP connectors, OCR, email/SMS notifications, automated
recalls, multi-importer tenancy, and n8n automation.


## Backend workflow enforcement (2026-10-16)

- Every triage result requires a new importer approval; supermarket forwarding is a separate decision.
- Approvals apply only to the latest run and its saved input versions. Old decisions never approve new results.
- Traceability requires current approved triage without an outstanding information request.
- Escalation requires a current approved shipment plan and completed findings from all assigned supermarkets.
- More-check recommendations reopen the selected supermarket tasks after approval; monitoring sends no manufacturer packet.
- Only an approved manufacturer-escalation recommendation creates the manufacturer inbox item.
- `POST /api/v1/cases/{id}/information` accepts notes and optional corrected product_name/batch_number.
  Saving information invalidates earlier proposals; rerun triage and review the new result.
  Identity corrections are blocked once retailer tasks exist.
- Case detail includes backend-authoritative `workflow` gates, proposal `review_block_reason`,
  named supermarket progress, and the manufacturer's response.
- Final verdict/closure requires a manufacturer response and reviewer notes. Operational statuses
  cannot bypass proposal approvals through the status endpoint.
- Existing historical decisions are retained. Runs predating input snapshots need a new run and review.
- Notifications remain in-app task queues; external email/SMS dispatch is not implemented.

## Clean local test baseline (2026-10-16)

The local SQLite database was reset after saving a backup outside the repository.
It starts with zero complaints, evidence uploads, agent runs, proposals, approvals,
retailer inspections, manufacturer escalations, and prior login sessions.
Demo seed data remains: 5 staff accounts, 1 product, 2 batches, and 4 shipments.
Submit a new public photo complaint to begin the full workflow. Existing browser
sessions must sign in again because database user/session IDs were recreated.
Groq configuration remains in the ignored `.env`; agent mode stays `llm`.
The local database and backup are not committed. A fresh checkout needs migrations
and demo seeding to reproduce this baseline; see the existing run instructions.
