# Frozen Scope Verification (WS1)

## Hashes reconfirmed before any edit

| File | Frozen hash (2F-34) | Confirmed live |
|---|---|---|
| `slice-2f35-module-scope.csv` (Set A) | `d1ad1fa8027272e1` | ✓ match |
| `slice-2f35-held-scope.csv` (Set B) | `4fb3739e9ace9269` | ✓ match |
| `slice-2f35-exclusion-scope.csv` (Set C) | `43a129bd966687b6` | ✓ match |
| Canonical inventory | `d4900ce03daa5437` | ✓ match |
| Matrix | `abfa5d030b1cfeee` | ✓ match |
| Held registry | `3729aa0e0fd5dafe` | ✓ match |

All frozen hashes matched exactly before any code or canonical change was
made this slice. No `FROZEN_SCOPE_MISMATCH`.

## Route sets, loaded verbatim (not recreated from memory)

**Set A** (2 routes):
- `DELETE /v1/webhooks/endpoints/{endpoint_id}` (`webhook_endpoint_management`)
- `POST /v1/rag/query` (`rag_query`)

**Set B** (9 routes):
- `security` module (2): `POST /v1/security/api-keys/{key_id}/rotate`,
  `POST /v1/security/api-keys/{key_id}/revoke`
- `documents` module (3): `POST /v1/documents`, `POST /v1/documents/
  {document_id}/send`, `POST /v1/documents/{document_id}/void`
- `rag` module (4): `DELETE /v1/rag/knowledge-bases/{kb_id}`, `POST
  /v1/rag/knowledge-bases/{kb_id}/documents`, `DELETE /v1/rag/documents/
  {doc_id}`, `POST /v1/rag/documents/{doc_id}/reindex`

**Set C**: 21 rows, loaded from `slice-2f35-exclusion-scope.csv`, none
modified this slice.

## Mount confirmation

All 11 scoped routes confirmed mounted via `authority_model_2f26e.py::
route_index()` both before and after this slice's edits. No route
appears in more than one scope set (verified programmatically — `SET_A`,
`SET_B` are disjoint by construction from the frozen CSVs).

Every Set A route had a canonical inventory row before this slice (the
existing unprotected rows). Every Set B route was confirmed outside
canonical coverage before adjudication.

## Application-file baseline

`git status --porcelain app/` line count immediately before any edit:
**65** (unchanged carry-forward from Slice 2F-34's end state).
