# Deferred Items

- Implementation of `geo_zone_management` (the selected module) — the
  future implementation slice, per
  [selected-module-implementation-contract.md](selected-module-implementation-contract.md).
  Not executed this slice.
- Adjudication of `create_zone`/`update_location` (geo module held
  candidates) — see [held-route-adjudication-contract.md](held-route-adjudication-contract.md).
- Adjudication of the remaining 56 pending held candidates outside the
  geo module.
- The N01 domain-integrity backlog (`confirm_upload` storage-existence
  verification, expired-session cleanup, media quota GET tenant-trust
  tightening) — see [n01-domain-integrity-backlog.csv](n01-domain-integrity-backlog.csv).
- Service-layer inspection of the 6 modules marked `UNKNOWN` in the risk
  scoring (see [known-limitations.md](known-limitations.md)).
