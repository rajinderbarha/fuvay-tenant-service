# Known Limitations

- **`POST /v1/payments/tenants/{tenant_id}/payout`'s `amount` field
  remains fully client-supplied** with no authoritative balance ledger
  to validate against. Tenant-trust/authorization is closed; financial-
  integrity is not. See `product-decisions-required.md`.
- **`InventoryService.receive_stock`'s `item_id`/`location_id` are still
  not cross-checked against the trusted tenant** (pre-existing gap noted
  in Slice 2F-36's own known-limitations.md, unrelated to and unchanged
  by this slice).
- **N01 domain-integrity backlog (4 items) remains fully open and
  unremediated** — this slice's mission prompt asked for active
  remediation, but the frozen Slice 2F-34 contract explicitly forbids
  touching N01 media files and instructs freezing (not remediating) the
  backlog. Followed the frozen contract. See `n01-final-status.md` for
  the full reasoning.
- **`app/engines/pricing/service.py`'s `receive`-adjacent read routes**
  (e.g. `get_zone`, `get_rule`) were not audited for tenant scoping this
  slice — only the 4 held mutation routes (`update_zone`, `delete_zone`,
  `update_rule`, `delete_rule`) were in scope. A cross-tenant read on
  `GET /v1/pricing/tenants/{tenant_id}/zones/{zone_id}` (by zone_id alone,
  same as the pre-fix mutation gap) may still be possible — flagged for
  a future read-path hardening pass, out of this slice's mutation-
  enforcement scope.
- Migration 144 remains unapplied, per mission OUT-OF-SCOPE list.
- `readonly@demo-ac-services.local` remains untouched, per mission
  PRESERVE list.
