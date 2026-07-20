# Held-Candidate Arithmetic (WS17)

## Reconciliation, from route keys

Starting: 54 pending (per Slice 2F-34's reconciliation).

All 9 frozen Set B routes received a final adjudication this slice —
`TENANT_PROVIDER_MUTATION_ADD` for all 9, each added canonically and
fully protected in this same slice (no route was added and left
unremediated):

```
POST   /v1/security/api-keys/{key_id}/rotate
POST   /v1/security/api-keys/{key_id}/revoke
POST   /v1/documents
POST   /v1/documents/{document_id}/send
POST   /v1/documents/{document_id}/void
DELETE /v1/rag/knowledge-bases/{kb_id}
POST   /v1/rag/knowledge-bases/{kb_id}/documents
DELETE /v1/rag/documents/{doc_id}
POST   /v1/rag/documents/{doc_id}/reindex
```

```
54 pending held candidates (start of 2F-35)
 - 9 resolved this slice (all TENANT_PROVIDER_MUTATION_ADD)
= 45 pending held candidates (end of 2F-35)
```

`r = 9` (routes receiving a final disposition). `final_pending_held = 54
- 9 = 45`.

## Proof

- All 9 resolved routes confirmed `VERIFIED` in the canonical CSV.
- No pending route (of the remaining 45) is canonical (verified: zero
  intersection between the 45 pending keys and the canonical CSV's route
  keys).
- Full row-level detail:
  [held-registry-before-after.csv](held-registry-before-after.csv).

## Forward assignment (unchanged)

The remaining 45 pending candidates retain their Slice 2F-34 assignment:
28 to Slice 2F-36, 17 to Slice 2F-37. This slice did not reassign or
touch any candidate outside its own frozen 9-route Set B.
