# Frontend and Mobile Caller Audit — Slice 2F-22

## Method

Two independent searches were run; the second was specifically used to check
the first had not missed a caller.

1. **Targeted search** — `mark_paid` and the purchase path across `.ts`,
   `.tsx`, `.js`, `.jsx`, `.dart` (excluding `node_modules`). Seven files
   matched; six were backend or test files.
2. **Exhaustive search** — the same file types across *all* non-`node_modules`
   directories, **including compiled `.next` build artifacts**, using a looser
   path pattern (`packages/.*purchase`).

The exhaustive pass surfaced one source file the targeted pass had not:
`frontend/super-admin/lib/api.ts`. It was inspected directly and calls only
`/v1/commerce/tenants/{id}/wallet/purchase/initiate|confirm`
(`platform_commerce` — a distinct model, unaffected by this slice) and
`GET /v1/admin/packages/purchases` (a read). **It does not call the route this
slice modified.** All other additional matches were compiled `.next` output
derived from the same two sources, not independent callers.

Two findings from the exhaustive pass:

- **`mark_paid` appears ZERO times** across every frontend source file *and*
  every compiled build artifact. Nothing in any shipped bundle has ever sent
  it.
- Exactly **one** caller of `POST /v1/tenant/packages/{package_id}/purchase`
  exists repository-wide (`frontend/tenant-portal/lib/api.ts:2471`).

No frontend calls `admin_purchase_package` at all, so the
`payment_authority` argument added to that handler has no client-facing
impact (its HTTP contract is unchanged in any case).

## The single caller

**Application:** `frontend/tenant-portal`
**File:** `lib/api.ts`, `providerPackageApi.initiatePurchase`

```ts
initiatePurchase: (packageId: string, paymentReference?: string) =>
  apiFetch<TenantPackagePurchase>(
    `/v1/tenant/packages/${packageId}/purchase`,
    { method: "POST", body: JSON.stringify({ payment_reference: paymentReference }) }
  ),
```

| Property | Finding |
|---|---|
| Persona | tenant portal — tenant owner |
| Request body | `{ payment_reference: <optional> }` |
| **`mark_paid` value** | **never sent** — the field appears nowhere in any frontend or mobile source |
| Amount / price fields | none sent |
| Package source | `packageId` from the backend-provided package list |
| Success handling | treats the response as a submitted request |
| Payment UX | none — there is no checkout flow for `ServicePackage` |
| Activation expectation | none — the method is named `initiatePurchase`, matching a pending selection |
| Retry behavior | none beyond user re-click (backend rejects duplicates) |

## Compatibility assessment — no frontend change required

- **`mark_paid`**: never sent by any caller, so rejecting it breaks nothing.
  The dangerous field existed only as an untyped backdoor on the server.
- **`payment_reference`**: the caller passes it as an *optional* parameter.
  When the argument is omitted, `JSON.stringify({ payment_reference: undefined })`
  serialises to `"{}"` — the key is dropped entirely, so the request remains
  valid under `extra="forbid"`. It is only rejected when a caller actually
  supplies a value, which is precisely the unverifiable attestation this
  slice removes.
- Mobile apps: **no caller found** for this route in any Dart source.

**No frontend or mobile file was modified.** No redesign was performed. The
prohibition on frontend work was honoured, and none was needed.

## Requirements check

- Frontend must not send `mark_paid=True` — satisfied; it never did.
- Frontend must not assume purchase equals payment success — satisfied; the
  method is `initiatePurchase` and no activation is assumed.
- Read-only actors see no purchase control — **not verified**; component-level
  UI gating was not audited (the backend now denies read-only scope
  regardless, which is the load-bearing control). Recorded honestly in
  `known-limitations.md` rather than claimed.
- Package price displayed comes from backend — satisfied; prices come from
  `GET /v1/tenant/packages/available`.
- Backend remains authoritative — satisfied.

## Disposition

`FRONTEND_CALLER_PRESENT_AND_COMPATIBLE` — one caller, already compatible,
unmodified.
