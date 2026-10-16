# BatchBridge implementation plan

## Current focus: backend

- [x] Lock product scope, roles, human gates, and safety rules.
- [x] Save the frontend reference and stable product context.
- [x] Add deployment-ready Python project and container contract.
- [x] Implement database schema and migration.
- [x] Seed the complete fictional supply chain.
- [x] Implement session authentication and role checks.
- [x] Implement public reports, staff cases, CSV imports, retailer findings, and manufacturer response.
- [x] Implement read-only MCP investigation tools.
- [x] Implement LangGraph investigation, bounded Groq assessment, and explicit human approval boundary.
- [x] Add audit events, idempotency, authorization tests, and exact-batch tests.
- [x] Run lint, tests, and migration checks.
- [ ] Run container smoke check on a machine with Docker available.

## Frontend follow-up

- [ ] Create React/Vite/Tailwind application from `FRONTEND_REFERENCE.md`.
- [ ] Connect generated API client to `/api/v1`.
- [ ] Build public, importer, retailer, and manufacturer flows.
- [ ] Add mobile and laptop responsive checks.

## Deployment gate

- [ ] Create Alternate Clouds PostgreSQL template service.
- [ ] Create and link application service.
- [ ] Set secrets and URLs before rebuild.
- [ ] Rebuild, then deploy.
- [ ] Verify health, migrations, login, complete demo workflow, and persistence across redeploy.

