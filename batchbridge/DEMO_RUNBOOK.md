# BatchBridge demo runbook

## Demo goal

Show that an importer can turn one suspected complaint into a traceable international batch
investigation while AI gathers evidence and humans control every safety action.

## Seeded story

- Product: fictional chocolate, SKU `CHOC-100`.
- Suspected manufacturer lot: `38`.
- Quantity received: 10,000.
- Retailer A received 3,000, Retailer B received 2,000, and Retailer C received 1,000.
- The importer retained 4,000.
- Retailer D received only lot `39` and must not be included in lot `38` tasks.

## Accounts

All seeded accounts use the deployed `DEMO_PASSWORD`.

- `importer@batchbridge.demo`
- `retailer-a@batchbridge.demo`
- `retailer-b@batchbridge.demo`
- `retailer-c@batchbridge.demo`
- `manufacturer@batchbridge.demo`

## Presentation path

1. Submit a public customer complaint for the chocolate and lot `38`.
2. Save the returned tracking token and show the customer tracking page.
3. Sign in as the relevant retailer safety manager, inspect the complaint, add notes or evidence,
   and forward it to the importer.
4. Sign in as the importer and open the case timeline.
5. Start the investigation and show the agent run steps.
6. Show the MCP evidence: matched product, exact lot, related reports, and shipment recipients.
7. Point out that Retailer D is absent because it received lot `39`.
8. Approve the proposal as the importer. Confirm that inspection tasks are created only now.
9. Sign in as one assigned retailer and submit a human finding.
10. Return as the importer and approve manufacturer escalation.
11. Sign in as the manufacturer, review the packet, and submit a response.
12. Return as the importer, record the final verdict, and close the case.
13. Show the complete audit timeline and the public tracking update.

## What to emphasize

- A customer can report directly, but a report starts an investigation rather than proving
  contamination.
- Shipment recipients come from importer records through MCP tools.
- The model summarizes and recommends; it cannot dispatch tasks, contact the manufacturer, or mark a
  batch contaminated.
- Each handoff shows the responsible human, timestamp, evidence, and decision.
- The same workflow accepts a retailer-originated inspection report.

## Pre-demo checklist

- [ ] Deployed `/health/live` and `/health/ready` return success.
- [ ] PostgreSQL is linked and demo data is present.
- [ ] Staff login works with `DEMO_PASSWORD`.
- [ ] Groq key is configured, or the deterministic fallback has been rehearsed.
- [ ] Lot `38` returns Retailers A, B, and C only.
- [ ] Evidence upload works with a small sample image or PDF.
- [ ] The full workflow has been completed once on the deployed environment.
- [ ] The browser has tabs ready for customer, importer, retailer, and manufacturer views.

## Fallback demo

Keep one pre-created case at each major stage. If an external model call fails, continue with the
stored deterministic proposal and explain that operational records remain authoritative. If a live
upload fails, use the existing evidence record and continue through approval and escalation.
