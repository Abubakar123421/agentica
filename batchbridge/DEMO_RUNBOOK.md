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

1. On the public form, click **Try with a demo photo**. This adds fictional chocolate packaging,
   selects CityMart Islamabad, and fills a sample complaint. Submit the photo report without entering
   any product or batch code.
2. Save the returned tracking token and show the customer tracking page.
3. Sign in as `retailer-a@batchbridge.demo`, open the unidentified complaint and inspect its photo.
   Under **Verify, then forward**, enter `DEMO-CHOC-38` (or click **Use demo code**) and select
   **Look up demo barcode**. Explain that this is a simulated fixture, not image decoding. Confirm
   the product/lot checkbox, add notes, and select **Verify & forward to importer**.
4. Sign in as the importer and open the case timeline.
5. Review and explicitly approve the latest Triage Agent proposal, then start the Traceability Agent.
   If triage requests information, save the missing facts, rerun triage, and review the new proposal.
6. Show the MCP evidence: matched product, exact lot, related reports, shipment recipients, and
   explicitly excluded retailers.
7. Point out that Retailer D is absent because it received lot `39`.
8. Approve the proposal as the importer. Confirm that inspection tasks are created only now.
9. Sign in as each assigned retailer (A, B, C) and submit a human finding.
   Show the importer response counter and blocked escalation until all three respond.
10. Return as the importer and run the Escalation Agent. Review its recommendation.
    Approve a manufacturer packet only if recommended; follow-up checks reopen selected tasks,
    and monitoring sends no packet. Complete additional checks if requested, then rerun escalation.
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
- [ ] Groq key is configured in `.env` and `AGENT_MODE=llm`; restart after setting variables.
- [ ] Fresh agent cards show Groq, model name and model turns, rather than previous demo rules.
- [ ] Lot `38` returns Retailers A, B, and C only.
- [ ] Evidence upload works with a small sample image or PDF.
- [ ] The full workflow has been completed once on the deployed environment.
- [ ] The browser has tabs ready for customer, importer, retailer, and manufacturer views.

## Fallback demo

Keep one pre-created case at each major stage. If an external model call fails, show the explicit
failure and a previously completed Groq run. Offline simulation requires explicitly selecting
`AGENT_MODE=demo` and labeling it as simulation; never present that as a live model investigation.
If a live upload fails, use an existing evidence record and continue through approval and escalation.

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
