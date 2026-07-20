# Frontend Helper Design — Slice 2F-9B (Workstream 3)

## Location
`frontend/tenant-portal/lib/api.ts`, immediately after `canIssueProviderInvoice`
(the closest existing precedent: a TENANT_OWNER_ONLY, mutation-scope-aware
helper for a single provider mutation).

## Signature
```ts
export const PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES = [
  "awaiting_provider_response",
  "under_admin_review",
] as const;

export function canOfferProviderComplaintResolution(
  role: string | null | undefined,
  status: string | null | undefined,
  accessScope: string | null | undefined = getAccessScope(),
): boolean {
  if (accessScope === "customer_support_limited") return false;
  if (!isTenantOwnerRole(role)) return false;
  if (!status) return false;
  return (PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES as readonly string[]).includes(status);
}
```

## Why this reuses, not duplicates, the existing framework
- `isTenantOwnerRole` is the same role check used by `canManageProviderInvoices`/
  `canIssueProviderInvoice`/the page's own pre-existing `canMutate`. Its
  "role === undefined -> treat as owner" loading-state convention is
  preserved unchanged (an established, intentional pattern for the
  `/auth/me`-in-flight window, not something this slice introduced or
  needs to alter) — a genuinely unknown role string (e.g. `"foo"`) still
  correctly returns `false` because it matches neither `"tenant_owner"`
  nor `undefined`.
- The `accessScope === "customer_support_limited"` check is copied
  verbatim from `canIssueProviderInvoice`, not reinvented.
- No second authorization framework, no new role concept, no new access
  scope value was introduced.

## Condition-by-condition mapping to the mission's 6 requirements
1. **Approved tenant-owner persona** → `isTenantOwnerRole(role)`.
2. **Mutation-capable access scope** → `accessScope !== "customer_support_limited"`.
3. **Not explicitly denied where effective permissions apply** → no
   `COMPLAINT_*` permission exists in the registry (confirmed unchanged
   since Slice 2F-9), so there is no permission-deny path to check; role +
   scope are the complete, correct condition set.
4. **Complaint belongs to current tenant context, where available** → not
   re-checked in this helper because the complaint detail page's own
   `GET /v1/provider/complaints/{id}` call already enforces tenant
   ownership server-side (`provider_get_complaint`) and the page returns
   early on `complaint.error` before any control renders — by the time
   `canOfferProviderComplaintResolution` is evaluated, `complaint.data`
   is guaranteed to belong to the caller's tenant, or the page has
   already shown the error state instead. Duplicating that check
   client-side would be redundant, not defense-in-depth (the data
   literally cannot be present otherwise).
5. **Status is one of the backend's exact legal source states** →
   `PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES.includes(status)`.
6. **Status is known and canonical** → the same `.includes()` check
   inherently rejects any status string not in the canonical list,
   including typos, legacy names, or unrecognized values.

## Fail-closed guarantee
Every one of staff / technician / customer / guest / read-only tenant
owner / unknown role / unknown access scope / missing status / unknown
status / any backend-rejected complaint state returns `false` — proven
directly in `lib/api.persona.test.ts` (21 new assertions, all passing;
see `frontend-test-matrix.csv`).
