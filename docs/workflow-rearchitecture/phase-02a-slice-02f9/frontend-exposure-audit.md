# Frontend Exposure Audit — Workstream 16

## Pages found
- `app/(tenant)/provider/complaints/page.tsx` — list page, no mutation
  controls (only a "View & Respond" link).
- `app/(tenant)/provider/complaints/[complaint_id]/page.tsx` — the real
  mutation surface: "Send reply," "Offer resolution," "Propose
  settlement," and "Accept"/"Reject" a settlement proposal.
- `app/(tenant)/provider/refund-requests/page.tsx` — confirmed read-only
  (list view; no `review`/mutation call found via grep).
- No dedicated rework-requests page was found in `frontend/tenant-portal`
  (the API client methods for schedule/start/complete rework, if they
  exist, were not located calling from any component).

## Finding: no role/access-scope gate on any of the 4 mutation controls (fixed this slice)
`complaints/[complaint_id]/page.tsx` had **zero** role check — every
authenticated tenant-portal user (owner or staff) saw and could invoke
"Send reply," "Offer resolution," "Propose settlement," and respond to
settlement proposals.

## Fix applied (minimal, reusing existing helpers)
```tsx
const canMutate = isTenantOwnerRole(getUserRole()) && !isTenantReadOnly();
```
Applied to: the header's "Propose settlement"/"Offer resolution" action
buttons, the reply input + "Send reply" button, and the
"Accept"/"Reject" settlement-proposal buttons. Same helper functions
reused from Slices 2F-7/2F-8 — no new frontend authorization system, no
visual redesign.

## Requirements check (after the fix)

| Requirement | Status |
|---|---|
| Read-only users have no active complaint mutation controls | Fixed — `isTenantReadOnly()` gates `canMutate` |
| Technicians see only explicitly approved assigned-job actions | N/A — no technician caller exists for this surface at all (confirmed, no mobile/staff-app reference); technicians see nothing, correctly |
| Staff sees only delegated capabilities | Fixed — no delegated capability was proven for staff (`require_tenant_owner_mutation` is owner-only), so staff now correctly sees no active controls either |
| Tenant owners see approved business-level actions | Preserved |
| Customer controls do not appear in provider surfaces | Confirmed — this page only calls provider-prefixed endpoints |
| Platform adjudication does not appear in tenant/provider surfaces | Confirmed — no admin-router call exists in this page |
| Internal notes do not appear in customer UI | N/A — no internal-note capability exists at all (see `note-evidence-privacy.md`) |
| Blocked service-credit/refund actions are not advertised as functional | The refund-requests page is read-only, correctly not advertising a "review" action that doesn't exist there |
| Backend remains authoritative | Confirmed — the fix is purely additive UI gating; backend 403s remain the real boundary |

## Conclusion
One real, minimal frontend misalignment found and fixed across 4
distinct controls on a single page. No visual redesign — same layout,
same component structure, only the render conditions changed.
