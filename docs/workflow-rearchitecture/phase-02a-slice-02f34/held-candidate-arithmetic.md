# Held-Candidate Arithmetic (WS2)

## Reconciliation, from route keys

Source: `docs/workflow-rearchitecture/phase-02a-slice-02f27a/
unauthorized-candidate-hold-registry.csv` — 59 data rows.

```
59 total held candidates
 - 3 resolved (N01 Set B, added canonically by Slice 2F-31)
 - 2 resolved (geo Set B, added canonically by Slice 2F-33)
= 54 pending (PENDING_MODULE_ADJUDICATION)
```

**54 matches the mission's expected pending count exactly.**

## Distribution of the 54 pending candidates by assigned future slice

Assigned by cross-referencing each candidate's `module` column (from the
2F-27a registry) against the module boundaries of the 10 remaining
canonical modules and their slice assignments:

| Assigned slice | Held-registry modules | Count |
|---|---|---|
| 2F-35 (critical/security-sensitive) | security, documents, rag | 9 |
| 2F-36 (enterprise/tenant-admin/operational) | appointments, ds, inventory, catalog, dispatch, settings, serviceability, chat, bookings, notifications | 28 |
| 2F-37 (financial/product-policy) | pricing, commerce, payments, subscriptions, compliance | 17 |

`9 + 28 + 17 = 54`. Every pending candidate is assigned to exactly one
future slice — none defaults to a generic "2F-38 review" bucket, since
every held-registry module matched one of the three implementation
slices' domains.

## Proof

- The 5 resolved routes (3 N01 + 2 geo) are confirmed `VERIFIED` in the
  canonical CSV.
- No pending route (of the 54) is canonical (verified: zero intersection
  between the 54 pending keys and the canonical CSV's route keys).
- Full row-level detail:
  [held-candidate-status-reconciliation.csv](held-candidate-status-reconciliation.csv).
