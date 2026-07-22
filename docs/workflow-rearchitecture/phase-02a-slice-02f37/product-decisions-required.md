# Product Decisions Required

## New this slice

**Payout amount-validation policy** (`POST /v1/payments/tenants/{tenant_id}/payout`):
what authoritative balance/ledger should a requested payout `amount` be
validated against? No such ledger exists anywhere in the codebase today.
Not resolved this slice — the tenant-trust/authorization dimension was
closed (`_require_trusted_tenant`), but the amount itself remains fully
client-supplied. Per the mission's canonical rule ("do not invent payout
or withdrawal behavior"), no balance-check policy was fabricated. See
`known-limitations.md` and `financial-domain-integrity-audit.csv`.

## Inherited from Slice 2F-34's registry, still open

- `compliance` deletion/portability candidates were assigned to 2F-37 —
  **resolved this slice**: an existing DPDP workflow was found already
  implemented, so no product-policy decision was required; only an
  authorization gap (missing self-only ownership check) was closed.
- N01 `confirm_upload` storage-existence verification approach — still
  unresolved, frozen (not remediated) per the actual 2F-34 contract.
- Expired upload-session / orphaned-storage cleanup ownership — still
  unresolved, frozen.
- Media quota GET tenant-trust tightening priority — still unresolved,
  frozen.
- Migration 144 application timing — deliberately deferred to Slice
  2F-38.
- `readonly@demo-ac-services.local` remediation approach — deliberately
  deferred to Slice 2F-38.
