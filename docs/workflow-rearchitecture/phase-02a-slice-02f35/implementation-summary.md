# Slice 2F-35 Implementation Summary

Critical Destructive and Security-Sensitive Authorization Batch, executed
strictly against the frozen Slice 2F-34 artifacts in
`docs/workflow-rearchitecture/phase-02a-slice-02f34/`. This is an
execution container: 4 independent modules, each with its own contract,
evidence, and final status.

## Set A (2 routes, both closed)

- `DELETE /v1/webhooks/endpoints/{endpoint_id}` (webhook_endpoint_management)
- `POST /v1/rag/query` (rag_query)

## Set B — held candidates (9 routes, all adjudicated, all fully protected)

- `security`: `POST /v1/security/api-keys/{key_id}/rotate`,
  `POST /v1/security/api-keys/{key_id}/revoke`
- `documents`: `POST /v1/documents`,
  `POST /v1/documents/{document_id}/send`,
  `POST /v1/documents/{document_id}/void`
- `rag`: `DELETE /v1/rag/knowledge-bases/{kb_id}`,
  `POST /v1/rag/knowledge-bases/{kb_id}/documents`,
  `DELETE /v1/rag/documents/{doc_id}`,
  `POST /v1/rag/documents/{doc_id}/reindex`

All 9 adjudicated `TENANT_PROVIDER_MUTATION_ADD` — each is a genuine
tenant-provider destructive/security mutation with no existing tenant
scoping; canonically added and fully protected in the same slice (per
mission rule: "do not add an included mutation canonically and silently
defer its security remediation").

## Mechanism

- New `_require_trusted_tenant(requested_tenant_id=None)` helper added to
  `WebhookService`, `RAGService`, `SecurityService`, `DocumentService`
  (mirrors the pattern established for `MediaService`/`GeoService` in
  earlier slices).
- `RAGService` additionally got `_get_kb_trusted(kb_id)`, kept separate
  from the original `_get_kb` so frozen Set C read routes are untouched.
- Router guards swapped `require_permission` →
  `require_tenant_mutation_permission` (10 routes) or the new-persona
  `require_mutation_access_scope` (1 route, `rag_query`, mixed-persona).
- One broken internal caller fixed: `app/engines/field_ops/service.py`'s
  invoice-generation call now passes `actor_tenant_id=job.tenant_id`.

## Coverage arithmetic

`c=2, a=9, h=9, r=9` → protected 241+2+9=252, denominator 264+9=273,
unprotected 273-252=21, pending held 54-9=45.

## Final status

**CRITICAL_AUTHORIZATION_BATCH_COMPLETE** — see `approval-gate.md`.
