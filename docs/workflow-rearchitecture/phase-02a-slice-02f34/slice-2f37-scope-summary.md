# Slice 2F-37 Scope Summary — Financial, Product-Policy and Remaining Held-Route Closure

## Modules (3 canonical routes)

- `platform_commerce_deposit` (3 routes: `GET /v1/commerce/tenants/
  {tenant_id}/deposit`, `POST .../deposit/initiate`, `GET .../deposit/
  transactions`). Cross-tenant path already closed at the service layer
  (`CommerceService._assert_owns_tenant_deposit`); the gap is narrowly
  the missing access-scope guard.

## Held candidates (17)

`pricing`(9), `commerce`(4), `payments`(1), `subscriptions`(1),
`compliance`(2). Full list:
[slice-2f37-held-scope.csv](slice-2f37-held-scope.csv). The `compliance`
candidates (`deletion-requests`, `portability-requests`) are explicitly
product-policy-dependent — do not invent policy; adjudicate only what
existing repository policy already supports.

## N01 domain-integrity backlog (separate sub-scope, not authorization)

- `confirm_upload` storage-existence verification
- Expired upload-session cleanup
- Orphaned-storage cleanup
- Media quota GET tenant-trust tightening

This sub-scope does NOT reduce N01's protected count and is not a
canonical-coverage item — it is a parallel, explicitly separate backlog
that must remain visible. See
[n01-domain-integrity-scope.md](n01-domain-integrity-scope.md).

## Full A/B/C sets and hashes

See [slice-2f37-scope-hashes.md](slice-2f37-scope-hashes.md).

## Full implementation contract

See [slice-2f37-implementation-contract.md](slice-2f37-implementation-contract.md).
