# Frontend and Mobile Caller Audit — Slice 2F-24

## Correction to an earlier draft of this document

An initial draft of this file claimed **"no frontend or mobile caller was
found"** and classified the surface `FRONTEND_MUTATION_SURFACE_ABSENT`. That
was **wrong**. A follow-up glob search over `frontend/**/lib/**` found three
caller files, one of which calls a route this slice changed **and sent the
exact field this slice removed**. The claim was retracted before this slice
closed; it is recorded here because a false "no callers" finding is precisely
the kind of error that ships a breaking change.

## Callers found

| Application | File | Endpoint | Relation to this slice |
|---|---|---|---|
| customer-app | `lib/api/customer-reviews.ts` → `app/customer/reviews/page.tsx` | `POST /v1/customer/reviews/{id}/flag` | **CALLS A CHANGED ROUTE** |
| tenant-portal | `lib/api.ts` (~934) | `POST /v1/reviews/{id}/reply`, `/flag` | **LEGACY engine** — not a changed route |
| super-admin | `lib/api.ts` (~2331) | `POST /v1/reviews/{id}/flag` | **LEGACY engine** — not a changed route |

**No caller exists** for either selected provider mutation
(`/v1/provider/reviews/{id}/reply`, `/v1/provider/reviews/{id}/flag`).

## The one incompatibility, found and corrected

`customer-reviews.ts` sent the client tenant:

```ts
export async function flagReview(
  reviewId, reasonCode, reasonText?, tenantId?,
) {
  body: JSON.stringify({ reason_code, reason_text, tenant_id: tenantId })
}
```

and `page.tsx:72` passed a real value: `flagReview(flagging.id, "other",
flagReason, flagging.tenant_id)`.

Since `CustomerFlagRequest` now rejects `tenant_id` (`extra="forbid"`), that
page would have started returning **422** — a user-visible break introduced by
the security fix.

**Minimal compatibility correction applied** (exactly two lines, no redesign,
as the mission permits):
1. `flagReview` — `tenantId` parameter and body field removed.
2. `page.tsx` — the fourth argument dropped from the call.

No layout, component, styling or behaviour changed. The page still flags a
review with the same reason data; it simply no longer asserts a tenant it has
no authority over.

## The two legacy callers — deliberately untouched

tenant-portal and super-admin call `/v1/reviews/{id}/reply|flag`, which is the
**legacy** `app.engines.review` engine operating on the separate `reviews`
table (`DISTINCT_MODEL`). This slice changed nothing there, so those callers
are unaffected.

This does sharpen a finding recorded in
`customer-review-alternate-route-audit.md`: the legacy engine's `flag_review`
carries the *same* unguarded shape as the defect fixed here (primary-key-only
lookup behind bare `get_current_user`) and — unlike the retired 410 create
route — **it has live frontend callers in two applications**. It remains
`DISTINCT_MODEL` and therefore outside this slice's permitted change boundary,
but it is a stronger future-slice candidate than the earlier "orphaned legacy"
framing suggested. Recorded in `known-limitations.md` and `deferred-items.md`.

## Requirements check

| Requirement | Status |
|---|---|
| Customer UI does not call provider reply | MET — no caller for either provider route |
| Provider UI does not send tenant identity as authority | MET — no provider caller exists |
| Customer flag UI does not send a trusted tenant ID | **MET, after correction** — it did; now removed |
| Read-only actors see no mutation controls | **NOT VERIFIED** — component-level gating not audited; the backend `access_scope` denial is the load-bearing control |
| Final-state actions hidden or disabled | **NOT VERIFIED** — same reason |
| Backend remains authoritative | MET |

The two unverified rows are reported as unverified rather than claimed.
