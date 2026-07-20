# Documentation Corrections — Slice 2F-24

## 1. Slice 2F-23's findings — all CONFIRMED, one understated

Every 2F-23 finding was verified against source before being acted on:

| 2F-23 finding | Verdict |
|---|---|
| `_get_review` filters only by `CustomerReview.id` | **CONFIRMED** |
| provider `flag_review` bare-authenticated, no ownership check, sets status | **CONFIRMED** |
| `submit_reply` lets a customer post the provider reply | **CONFIRMED** |
| that action attributed as `ACTOR_PROVIDER` | **CONFIRMED** |
| `customer_router.flag_review` accepts client `tenant_id` | **CONFIRMED** |
| `CustomerReview` is the only review model in scope | **CONFIRMED** |
| legacy `POST /v1/reviews` remains 410 | **CONFIRMED and preserved** |

**Understated:** 2F-23 did not identify that **both `GET /{review_id}` detail
routes were also unscoped** — a cross-tenant read IDOR exposing pending,
hidden, rejected and deleted reviews with their moderation and rejection
reasons. Found and fixed this slice. The 2F-23 selection remains correct; its
scope was narrower than the module's actual exposure.

## 2. This slice's own frontend audit was wrong in draft, and retracted

An initial `frontend-mobile-caller-audit.md` claimed **no frontend callers
exist** and labelled the surface `FRONTEND_MUTATION_SURFACE_ABSENT`. A
follow-up glob search found three caller files — including one that calls a
changed route **and sent the exact `tenant_id` field this slice removed**,
which would have produced a 422 on a live page.

The claim was retracted and the document rewritten to lead with the
correction, and a two-line compatibility fix was applied. Recorded prominently
because a false "no callers" finding is exactly how a security fix ships a
user-visible break.

## 3. Slice-2D canaries untouched
As required.

## 4. Historical artifacts preserved
2F-19, 2F-21 and 2F-23 slice CSVs are unmodified. Where a later slice
protected a route those CSVs record as unprotected, the exemption lives in the
*test* with the slice named — never by editing the historical record.

## 5. 2F-23's guard tests inverted rather than deleted
2F-23 wrote five assertions against live source specifically so its finding
could not rot before implementation. They fired when this slice fixed the
defect — working as designed. Each was **inverted** to assert the fixed state,
so the same protection now guards against reversion. Detailed in
`regression-report.md`.

## 6. Forward annotation added to Slice 2F-23
Per the established convention, `phase-02a-slice-02f23/approval-gate.md`
carries a new forward-annotation section.
