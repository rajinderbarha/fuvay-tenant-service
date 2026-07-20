# Slice 2F-35 Scope Summary — Critical Destructive and Security-Sensitive Authorization

## Modules (2 canonical routes)

- **webhook_endpoint_management** — `DELETE /v1/webhooks/endpoints/
  {endpoint_id}`. Client-asserted tenant_id never verified against actor.
- **rag_query** — `POST /v1/rag/query`. Zero tenant predicate on
  knowledge-base lookup; confirmed cross-tenant data-exposure risk.

## Held candidates (9)

- `security` module (2): `POST /v1/security/api-keys/{key_id}/rotate`,
  `POST /v1/security/api-keys/{key_id}/revoke`
- `documents` module (3): `POST /v1/documents`, `POST /v1/documents/
  {document_id}/send`, `POST /v1/documents/{document_id}/void`
- `rag` module (4): `DELETE /v1/rag/knowledge-bases/{kb_id}`, `POST
  /v1/rag/knowledge-bases/{kb_id}/documents`, `DELETE /v1/rag/documents/
  {doc_id}`, `POST /v1/rag/documents/{doc_id}/reindex`

## Why these are grouped

Both canonical routes and all 9 held candidates share the same severity
class this slice's evidence surfaced: either a client-asserted/absent
tenant boundary on a destructive or data-exposing capability, or a
security-domain administrative action (API-key rotation/revocation,
document send/void, knowledge-base management). None was included merely
to pad the route count — see
[remaining-module-risk-scores.csv](remaining-module-risk-scores.csv) for
the severity evidence behind each canonical inclusion.

## Full A/B/C sets and hashes

See [slice-2f35-scope-hashes.md](slice-2f35-scope-hashes.md).

## Full implementation contract

See [slice-2f35-implementation-contract.md](slice-2f35-implementation-contract.md).
