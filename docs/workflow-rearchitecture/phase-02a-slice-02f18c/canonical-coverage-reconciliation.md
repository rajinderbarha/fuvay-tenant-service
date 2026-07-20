# Canonical Coverage Reconciliation

## Starting approved baseline
190/226 (pre-2F-18) → 200/226 (2F-18/2F-18A/2F-18B, router-level guard
fix, unchanged by object/attachment-level deepening in each subsequent
slice).

## This slice's reconciliation of all 10 selected routes
See `final-selected-route-protection.csv` for the row-by-row table. All 10
routes are re-confirmed `FULLY_PROTECTED`:

- **Persona/mutation-scope status**: unchanged — re-confirmed via live
  runtime introspection (identical output to every prior slice in this
  series).
- **Media authority status**: **advanced this slice** — the one
  attachment-accepting route (`provider_send_message`) AND the newly-fixed
  `staff_send_message` (previously silently dropped its `media_ids`
  field, now fully wired through the same validated path) are both now
  genuinely fully protected on the SHARING dimension (view-vs-share
  distinction, thread-claim lineage lock) and the RETRIEVAL dimension
  (technician assignment/participant policy applied at retrieval time,
  privacy-equivalent errors).
- **Technician/recipient/retrieval status**: all newly closed this slice
  (see `technician-chat-media-policy.md`, `attachment-recipient-authority.md`,
  `media-retrieval-download-audit.csv`).

## Arithmetic — NOT automatically 200/226
Per the mission's explicit instruction not to force 200/226: this slice
independently re-verified all 10 routes individually. **190 (baseline) +
10 (all ten selected routes, individually confirmed fully protected,
including `staff_send_message` which is NOW a genuine attachment-capable
route for the first time) = 200.** The denominator (226) is unchanged —
no row was added, removed, or reclassified this slice.

**Result: 200/226 — re-earned with even stronger evidence than 2F-18B**,
since the previously-open sharing/recipient/retrieval/revocation
dimensions are now closed (or, where genuinely unclosable without a
schema change, explicitly and narrowly disclosed rather than silently
assumed).

## Both canonical CSVs recount identically
Unchanged from 2F-18/2F-18A/2F-18B — no row was touched this slice.
`tenant-mutation-endpoint-inventory.csv` (226 rows, 200 protected) and
`mutation-enforcement-matrix.csv` remain exactly as 2F-18 left them.
`test_canonical_totals` and
`test_global_numerator_denominator_match_2f17_baseline` (both asserting
`total==226, protected==200`) pass unchanged, re-confirmed by this slice's
regression run.

## Remaining module count
Unchanged: 26 unprotected tenant/provider mutation routes across the 10
non-selected modules — this slice touched only `platform_notifications`
and the narrowly-scoped `app/engines/media/asset_service.py` correction.
