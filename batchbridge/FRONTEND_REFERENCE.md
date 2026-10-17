# Frontend reference

Reference requested by the project owner:

- [VoltAgent repository README](https://github.com/voltagent/voltagent)
- [Raw README Markdown](https://raw.githubusercontent.com/VoltAgent/voltagent/main/README.md)

Use it as visual and information-architecture inspiration only. Do not copy its branding or text.

## Cues to carry into Escalera

- Clear product statement and one primary action above the fold.
- Short navigation with product, workflow, demo, and documentation destinations.
- Evidence-first dashboard: case status, timeline, agent trace, and approvals are visible without
  opening several screens.
- Workflow runs show individual steps and their outcomes, similar to an agent operations console.
- Compact badges for role, state, confidence, and human approval.
- Responsive cards on mobile; use tables only where shipment comparison genuinely needs them.
- Keep the public complaint form calm and simple. Keep operational depth inside authenticated views.

## Escalera screen map

1. Public report and private tracking page.
2. Staff login.
3. Importer dashboard and data imports.
4. Case detail with evidence, MCP trace, proposal, approval, and audit timeline.
5. Retailer inspection inbox and finding form.
6. Manufacturer escalation inbox and response form.


## Implemented workflow feedback

- Stage run buttons use backend `workflow` gates and display concrete blocker reasons.
- A stage without a run shows Ready when eligible, rather than always Locked.
- Triage displays Groq/model/turn metadata; tracing/escalation display Rule-based / MCP / No LLM.
- Saving facts explicitly states that fresh triage is required. A changed input snapshot is
  distinguished from a missing human approval.
- Importer detail shows named retailer response counts/findings, pending proposal actions,
  manufacturer response, and final human closure controls.
- Final browser keyboard/viewport verification remains pending.
