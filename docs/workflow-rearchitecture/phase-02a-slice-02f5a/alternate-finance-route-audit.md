# Alternate Route and Duplicate System Audit — Workstream 9

## Security deposit: package_commerce vs. finance_hub
`package_commerce.admin_router`'s `admin_mark_deposit_paid`/
`admin_refund_deposit`/`admin_forfeit_deposit` are `DEPRECATED_410` —
confirmed dead (always raise `HTTPException(410)` before touching any
model), with an explicit docstring naming `finance_hub` as canonical.
**Disposition: `CANONICAL_PLATFORM_WRITE` for `finance_hub.admin_router`;
`DEPRECATED` for the 3 `package_commerce` stubs.** No live duplicate
exists — the weaker "alternate" was already neutralized by a prior slice,
not this one.

## Package purchase: admin vs. tenant self-service
`package_commerce.admin_router.admin_purchase_package` and
`package_commerce.tenant_router.tenant_purchase_package` both call the
identical `PackageCommerceService.create_package_assignment` method,
writing to the same canonical `TenantPackageAssignment` table.
**Disposition: `CANONICAL_TENANT_WRITE` shared by two personas** (admin
recording on tenant's behalf; tenant self-service) — not two competing
write owners, a single shared canonical method. No closure action needed.

## Credit wallet: package_commerce vs. usage_credits
`package_commerce.admin_router`'s wallet endpoints delegate entirely to
`app.engines.usage_credits.service.UsageCreditService`.
**Disposition: `CANONICAL_PLATFORM_WRITE` is `UsageCreditService`;
`package_commerce.admin_router` is a thin, already-migrated adapter over
it** (per the FINAL-L5-05J fix referenced in its own code comments) — not
a duplicate write owner.

## Commission: package_commerce only
No alternate commission-calculation/deduction route was found elsewhere
in the searched modules (`finance_hub`, `platform_commerce`, `billing`,
`subscription`, `invoice`, `reconciliation`, `tenant_engine`,
`provider_portal`, `customer_credits`) this slice.
**Disposition: `CANONICAL_PLATFORM_WRITE`**, sole implementation found.

## Payouts / warranty claims: finance_hub only
No alternate implementation was found for either capability elsewhere.
**Disposition: `CANONICAL_PLATFORM_WRITE`**, sole implementation, but
**`BLOCKED_PENDING_FINANCE_OWNERSHIP_DECISION`** in the sense that the
underlying permission is granted to no operational role — the write owner
is unambiguous, but its intended operator (`admin_finance`?) cannot
currently reach it.

## Conclusion
**No live, exploitable weaker alternate financial write route was found
in either module.** The one apparent duplicate (security deposit) was
already resolved by a prior slice's `DEPRECATED_410` closure. No new
consolidation or closure action is required this slice.
