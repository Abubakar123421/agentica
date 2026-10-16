# Alternate Clouds deployment

Official references:

- Dashboard: <https://clouds.alternatefutures.ai>
- Documentation: <https://docs.alternatefutures.ai>
- CLI: <https://www.npmjs.com/package/@alternatefutures/acc>

## 1. Prepare

Push `batchbridge/` to its own GitHub repository or set it as the service root directory. Keep all
secrets out of Git.

```bash
npm install -g @alternatefutures/acc
acc login
acc whoami
acc projects create --name batchbridge
```

## 2. Create PostgreSQL

```bash
acc services create --kind template --template postgres
```

Set a strong `POSTGRES_PASSWORD`. The template uses PostgreSQL 17 and persistent storage at
`/var/lib/postgresql/data`. Record the database service ID.

## 3. Create the application service

Use the dashboard GitHub flow or the equivalent CLI command:

```bash
acc services create \
  --kind github \
  --repo OWNER/REPOSITORY \
  --github-installation INSTALLATION_ID \
  --branch main \
  --root-directory batchbridge
```

Link the application service to PostgreSQL with alias `DB`; this exposes `DATABASE_URL` and the
individual `PG*` values:

```bash
acc services link APP_SERVICE_ID DATABASE_SERVICE_ID --alias DB
```

## 4. Set environment variables

```bash
acc services env set APP_SERVICE_ID APP_BASE_URL https://APP-SLUG-app.alternatefutures.ai
acc services env set APP_SERVICE_ID SESSION_SECRET A_LONG_RANDOM_VALUE
acc services env set APP_SERVICE_ID GROQ_TRIAGE_API_KEY YOUR_TRIAGE_GROQ_KEY
acc services env set APP_SERVICE_ID GROQ_MODEL openai/gpt-oss-20b
acc services env set APP_SERVICE_ID AGENT_MODE llm
acc services env set APP_SERVICE_ID COOKIE_SECURE true
acc services env set APP_SERVICE_ID ALLOWED_ORIGINS https://APP-SLUG-app.alternatefutures.ai
acc services env set APP_SERVICE_ID SEED_DEMO_DATA true
acc services env set APP_SERVICE_ID DEMO_PASSWORD A_STRONG_DEMO_PASSWORD
```

## 5. Rebuild, then deploy

The organizer-required order is variables first, rebuild second, deploy third.

```bash
acc services rebuild APP_SERVICE_ID
acc services deploy APP_SERVICE_ID
acc services logs APP_SERVICE_ID --tail 100
```

## 6. Verify

1. `GET /health/live` returns `{"status":"ok"}`.
2. `GET /health/ready` returns `{"status":"ready"}`.
3. Log in with a seeded importer account and the deployed `DEMO_PASSWORD`.
4. Run the lot 38 demonstration through manufacturer response and importer closure.
5. Redeploy once and confirm the case, audit timeline, and response still exist.

For the hackathon, use synthetic data only. The template provides persistent PostgreSQL storage but
does not by itself prove managed backups, high availability, or a production disaster recovery SLA.


## Current hybrid configuration and verification status

Only triage needs Groq: use `GROQ_TRIAGE_API_KEY` or fallback `GROQ_API_KEY`. Do not provision
traceability/escalation keys; these stages always use rules and MCP. Never place actual keys
in shell history or Git; prefer dashboard secret entry when configuring the live service.

This document is a deployment checklist, not proof of deployment. The commands above have not
been rerun against the current cloud CLI during this documentation update. Confirm the current
platform instructions before executing them. Container smoke testing, live PostgreSQL persistence,
and full Alternate Clouds deployment verification remain pending.
