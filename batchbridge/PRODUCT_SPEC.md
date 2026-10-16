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

1. A customer reports a suspected issue through the public portal or to the retailer.
2. A retailer food safety manager inspects the item, adds evidence, and forwards the case.
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

- Accept product name, description, purchase retailer, purchase date, optional batch number,
  reporter contact details, and optional image or PDF evidence.
- Generate a public case ID and a random private tracking token.
- Allow retailer staff to create a case from an inspection without a customer report.

### Investigation

- Match aliases to a catalogue product.
- Resolve a batch only from product identity plus manufacturer lot number.
- List only retailers present in the importer's shipment records for the matched batch.
- Show uncertainty, sources, and the reason for each suggested action.
- Continue deterministically when the optional LLM is unavailable.

### Human gates

- An importer approves or rejects the agent proposal.
- Retailer checks are created only after approval.
- Manufacturer escalation requires an approved proposal and at least one completed human finding.
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
