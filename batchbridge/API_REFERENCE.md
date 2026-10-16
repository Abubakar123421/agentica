# BatchBridge API reference

All application endpoints are under `/api/v1` except health checks, the root response, OpenAPI JSON,
and Swagger UI. The running server provides the authoritative interactive contract at `/docs`.

## Public endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | Database readiness |
| `POST` | `/api/v1/reports` | Create a customer report and tracking token |
| `GET` | `/api/v1/tracking/{tracking_token}` | View public case progress |
| `POST` | `/api/v1/reports/{public_id}/evidence` | Upload report evidence with the tracking token |

Evidence uploads accept JPEG, PNG, or PDF files up to 5 MB.

## Authentication

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Create a server-side session cookie |
| `POST` | `/api/v1/auth/logout` | Revoke the current session |
| `GET` | `/api/v1/auth/me` | Return the signed-in staff user |

Browser clients must send cookies on authenticated requests.

## Shared staff endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/cases` | List role-scoped cases |
| `GET` | `/api/v1/cases/{case_id}` | Read case detail, evidence, proposals, findings, escalation, and timeline |
| `POST` | `/api/v1/cases/{case_id}/evidence` | Add authenticated evidence |
| `GET` | `/api/v1/evidence/{evidence_id}` | Download evidence when authorized |
| `GET` | `/api/v1/catalog/retailers` | List permitted retailer choices |
| `GET` | `/api/v1/catalog/products` | Search catalogue products |
| `GET` | `/api/v1/catalog/batches` | List role-scoped batches |
| `GET` | `/api/v1/catalog/shipments` | List role-scoped shipments |

## Retailer endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/cases/officer-report` | Create a case from a retailer inspection |
| `POST` | `/api/v1/cases/{case_id}/retailer-review` | Review and forward or hold a customer report |
| `GET` | `/api/v1/inspections` | List inspections assigned to the signed-in retailer |
| `POST` | `/api/v1/inspections/{inspection_id}/finding` | Submit a human stock-check finding |

## Importer endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/imports/templates/{kind}` | Download a batch or shipment CSV template |
| `POST` | `/api/v1/imports/batches` | Validate and import batch records |
| `POST` | `/api/v1/imports/shipments` | Validate and import shipment records |
| `PATCH` | `/api/v1/cases/{case_id}/status` | Update case status or final human verdict |
| `POST` | `/api/v1/cases/{case_id}/analysis` | Queue an MCP-grounded investigation |
| `GET` | `/api/v1/cases/{case_id}/analysis/{run_id}` | Poll investigation status and result |
| `POST` | `/api/v1/cases/{case_id}/approvals` | Approve or reject an agent proposal |
| `POST` | `/api/v1/escalations/cases/{case_id}` | Send an approved evidence packet to the manufacturer |

Manufacturer escalation is rejected unless the case has an approved batch proposal and at least one
completed retailer finding.

## Manufacturer endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/escalations` | List escalations addressed to the signed-in manufacturer |
| `POST` | `/api/v1/escalations/{escalation_id}/response` | Submit the manufacturer investigation response |

## MCP tools

The stdio server in `backend/app/mcp_server.py` exposes these read-only tools:

- `get_case(case_id)`
- `search_products(query)`
- `get_batch(product_id, batch_number)`
- `find_related_reports(product_id, batch_number, exclude_case_id)`
- `get_batch_shipments(batch_id)`
- `get_inspection_findings(case_id)`

Tool output preserves database identifiers. Reporter contact details are intentionally absent.
