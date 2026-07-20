# Known Limitations

- **Ownership was not exhaustively re-inspected for `admin_catalog_
  provider_setup`'s `recommendation_router`/`service_option_provider_
  router` handlers** beyond confirming their guard chain and general
  tenant-derivation pattern — a future 2F-36 slice should perform the
  same depth of inspection as was done for `brand_provider_router` this
  slice.
- **`enterprise/exports`'s row-level scoping was not fully re-audited**
  — only the route-level and constructor-level tenant derivation was
  confirmed; the per-resource export permission gating referenced by an
  inline code comment was not independently re-verified line-by-line.
- **Held-candidate module bucketing (2F-35/36/37 assignment) was done at
  the held-registry's existing `module` label level, not per-route
  source inspection** — each future slice must still perform its own
  WS3-style direct-evidence adjudication before closing any held route;
  this slice's assignment is a scope freeze, not a pre-adjudication.
- **This reconciliation is scoped to the 23-route canonical unprotected
  queue and the 59-route held registry only.** It does not re-audit any
  already-`VERIFIED` route (M01, N01, or geo), and does not re-open any
  of them.
