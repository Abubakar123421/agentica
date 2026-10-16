# BatchBridge product specification

## Problem

Food complaints often begin at one retailer while the importer holds the only complete record of
where a batch was distributed. Product names, supplier aliases, missing lot numbers, and separate
retailer systems slow the investigation. A complaint is also not enough evidence to declare an
entire batch contaminated.

BatchBridge gives the country importer one evidence-based workflow to receive reports, trace an
exact product and manufacturer lot, request checks from every retailer that received it, and send a
human-approved evidence packet to the manufacturer.

## Primary use case

1. A customer selects a supermarket and uploads product photos with a description of the problem.
2. The supermarket food safety officer reviews the images, previews a simulated barcode match,
   verifies the product and batch, and forwards the case with notes. This starts triage.
3. The importer starts an investigation.
4. The agent uses read-only MCP tools to match the product and batch and retrieve exact shipment
   recipients.
5. An importer investigator reviews the evidence and approves retailer inspection tasks.
6. Retailer safety managers inspect their stock and submit findings.
7. The importer approves an escalation to the overseas manufacturer.
8. The manufacturer responds with its investigation result.
9. The importer records the final human decision and closes the case.

Customers may submit reports directly. Their reports create a suspected case and never declare a
batch contaminated. Retailer staff and importer investigators have stronger workflow permissions,
but all safety decisions remain attributable to a named human reviewer.

## Users and permissions

| Actor | Main capabilities |
| --- | --- |
| Customer | Submit a report and evidence; track the case with a private token |
| Retailer food safety manager | Create inspection reports, review customer cases, add evidence, complete assigned stock checks |
| Importer investigator | Import batch and shipment data, run investigations, approve tasks and escalations, set final status |
| Manufacturer reviewer | Read evidence packets for its organization and submit a response |
| Agent | Read approved operational data through MCP, rank possible matches, explain evidence, and draft actions |

## MVP scope

- Public customer report and private tracking.
- Retailer-originated inspection report.
- Importer-owned products, aliases, batches, shipments, and recipient retailers.
- CSV import for batches and shipments.
- MCP-grounded investigation with product, batch, related-report, shipment, and finding lookups.
- Human approval before retailer tasks and manufacturer escalation.
- Role-scoped queues for retailers and manufacturers.
- Evidence uploads, case timeline, proposal history, decisions, and audit events.
- PostgreSQL deployment on Alternate Clouds.

## Functional requirements

### Reporting

- The customer UI accepts a supermarket, description, 1–3 JPEG/PNG photos (5 MB each), and optional
  purchase date/contact details. It does not ask the customer for product or batch codes.
- Retain the structured JSON reporting endpoint for existing clients and tests.
- Offer generated fictional packaging for the demo; clearly label the officer barcode lookup as
  simulated. Store a human verification event and use database-backed product/lot fixtures.
- For photo reports, require officer verification and forwarding before importer traceability.
- Generate a public case ID and a random private tracking token.
- Allow retailer staff to create a case from an inspection without a customer report.

### Investigation

- Match aliases to a catalogue product.
- Resolve a batch only from product identity plus manufacturer lot number.
- List only retailers present in the importer's shipment records for the matched batch.
- Show uncertainty, sources, and the reason for each suggested action.
- Use Groq for triage in LLM mode; traceability and escalation use deterministic MCP-backed rules.
- Validate operational identifiers and retailer assignments against actual MCP evidence.
- Show model summaries, follow-up questions, execution mode, model name and tool traces.
- Show failures explicitly when the LLM is unavailable; offline simulation requires `AGENT_MODE=demo`.

### Human gates

- An importer approves or rejects the agent proposal.
- Retailer checks are created only after approval.
- Manufacturer escalation requires an approved proposal and completed findings from every assigned retailer.
- The importer owns the final safety verdict and closure decision.

### Audit and privacy

- Record actor, event, timestamp, and relevant identifiers for each workflow change.
- Exclude customer contact details from MCP output, LLM prompts, and manufacturer packets.
- Scope retailer and manufacturer access to their own organization.
- Validate evidence type and size and protect staff mutations with authenticated sessions and origin
  checks.

## State model

Main path:

`new_report -> under_review -> retailer_checks -> manufacturer_review -> closed`

`waiting_for_information` may pause a case when required evidence is missing. The safety verdict is
tracked separately and starts as `unconfirmed`.

## Success criteria

- The importer can identify every recorded recipient of an exact batch in under one minute.
- A retailer that received another lot never appears in the affected-recipient list.
- Every external handoff has a recorded human approval.
- Judges can trace each agent conclusion to an MCP result or human-submitted finding.
- The complete lot 38 demo runs on the deployed Alternate Clouds URL.

## Non-goals for the hackathon

- Automatic recall issuance or legal determination.
- Laboratory diagnosis from a photo.
- Government regulator integrations.
- Live ERP, email, SMS, or barcode integrations.
- Multi-importer software-as-a-service tenancy.
- Production disaster recovery guarantees.

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
