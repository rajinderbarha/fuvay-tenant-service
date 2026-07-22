# Slice 2F-24 Approval Gate

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## SECURITY — CLOSED

| Requirement | Status | Evidence |
|---|---|---|
| Canonical provider persona | MET | `require_tenant_owner_mutation`; staff/technician/customer/guest denied |
| Mutation-capable scope | MET | read-only `access_scope` denied |
| Exact tenant/provider ownership | MET | `DIRECT_TENANT_COLUMN` via central scoped lookup |
| No primary-key-only authorization | MET | `_get_review` is admin-read only and documented as never an authorization boundary |
| No customer-as-provider reply | MET | persona guard |
| Server-derived actor identity and type | MET | JWT id + service allow-list |
| No client tenant authority | MET | `tenant_id` rejected by schema; flag tenant taken from the review |
| No cross-tenant / cross-provider mutation | MET | SQL predicate; foreign row never loaded |
| No weaker same-record route | MET | `customer-review-alternate-route-audit.md` |
| Runtime verifier exits zero | MET | `runtime-verification-report.md` |

The mission's bar — *"do not claim security closure while any authenticated
principal can mutate a foreign review"* — is satisfied: the cross-tenant path
is closed at the service layer, so a router regression alone cannot reopen it.

## DOMAIN INTEGRITY — CLOSED

| Requirement | Status |
|---|---|
| Review/reply/flag transitions explicit | MET — `customer-review-state-machine.csv` |
| Duplicate reply behaviour explicit | MET — one per review, `REPLY_ALREADY_EXISTS` before any write |
| Duplicate flag behaviour explicit | MET — documented; status written once, no aggregate effect |
| Invalid transitions fail before mutation | MET — `no-partial-persistence-proof.md` |
| Final states immutable per established policy | MET — provider/customer cannot reach admin outcomes |
| Rating aggregates not corrupted | MET — neither selected mutation touches an aggregate |
| Invalid actions create no partial state | MET — denial tests assert `db.add`/`flush`/`commit` never called |

The bar — *"do not claim domain-integrity closure while provider reply or
review flagging can corrupt final or aggregate state"* — is satisfied.

## PRIVACY — CLOSED

Two cross-tenant read IDORs were found **this slice** (not in the 2F-23
finding) and closed: both `GET /{review_id}` detail routes were unscoped
primary-key reads exposing pending, hidden, rejected and deleted reviews with
their moderation and rejection reasons. Foreign and missing ids are now
privacy-equivalent (`REVIEW_NOT_FOUND`), so no route is an existence oracle.
Customer and provider boundaries remain distinct — `require_customer` denies
tenant principals on the customer route, and vice versa.

## GLOBAL COVERAGE — CLOSED

**207/226 → 209/226.** 17 unprotected across 7 modules. Both selected routes
reconciled individually against all ten dimensions. Every numeric recount
assertion repo-wide located by grep and updated (6 files). Historical
point-in-time artifacts left truthful; where a later slice protected a route,
the exemption lives in the test with the slice named.

The customer flag route was corrected but **not counted** — `/v1/customer/`
prefix, outside the tenant-only CSV by the Design A convention.

## PRODUCT POLICY — BLOCKED (expected and permitted)

Staff persona for reply/flag; customer flagging of others' reviews; flag
deduplication; final-state flag policy; reply editing; flag reason taxonomy;
the legacy review engine's fate; moderation SLA, appeals, automated
moderation and retention. See `product-decisions-required.md`.

## Regression — proven across BOTH dimensions

| | BEFORE (2F-23) | AFTER | New | Resolved |
|---|---|---|---|---|
| failing node IDs | 86 | 86 | **0** | 0 |
| error node IDs | 111 | 111 | **0** | 0 |
| passed | 11146 | 11192 | +46 = exactly the new tests | |

First slice in this initiative able to compare **both** failures and errors at
node-ID level, using the `-rE` baseline 2F-23 captured for exactly this
purpose.

## Honest disclosures

- **My own frontend audit was wrong in draft.** It claimed no callers existed;
  three exist, and one sent the exact `tenant_id` field this slice removed —
  which would have 422'd a live customer page. Retracted, corrected, and a
  two-line compatibility fix applied. Recorded prominently in
  `documentation-corrections.md`.
- **2F-23 understated the module's exposure** — it did not identify the two
  read IDORs. Its selection was still correct.
- **The legacy `app.engines.review` engine keeps the same unguarded pattern**
  on its own table and has live frontend callers. `DISTINCT_MODEL`, outside
  the permitted boundary, explicitly not fixed — flagged rather than ignored.
- **No live database or server**; the fix is proven by SQL-predicate presence
  and by denial paths writing nothing, not by an executed exploit.

## Preserved (re-confirmed)

Legacy `POST /v1/reviews` still 410 (asserted); Package Commerce and
compliance closures asserted intact by test; platform-notifications, Booking,
quote-checklist, invoice-lineage and field_ops closures untouched;
`PartsRequest` ServiceJob-only; `Booking`/`ServiceBooking` and
`field_ops.Job`/`ServiceJob` separate; canonical roles only, no alias;
`readonly@demo-ac-services.local` untouched; Migration 144 unapplied;
Slice-2D canaries untouched.

## Scope discipline

No role, permission or migration added. No pipeline merged. No new review
engine or second review table. No moderation UI, notification infrastructure,
appeal workflow or automated moderation built. No rating formula changed. Five
application files changed, all within the proven review-authorization
boundary, plus two frontend lines for compatibility — no redesign.

## Stop condition

This response stops at the Slice 2F-24 approval gate. No other module has been
begun. **7 modules / 17 routes remain** —
`remaining-module-queue-update.csv`.

## Forward annotation (added by Slice 2F-25)
Slice 2F-25 resolved the legacy-engine gap this slice flagged. **This slice's
`DISTINCT_MODEL` classification was CORRECT** -- the tables really are
distinct (`reviews` vs `customer_reviews`), so it was not a same-record
bypass, and declining to touch it was the right scope call. The flag was also
warranted: the legacy exposure proved *larger* than the canonical engine's.

Legacy defects found and closed in 2F-25: cross-tenant mutation via
primary-key-only lookup on `submit_reply`/`flag_review`; bare authentication
on `flag_review`; client-supplied `tenant_id` accepted from query string, path
AND request body across six routes; and `_assert_owns` -- which only ever
fired for `actor_role == "customer"` -- being relied on as a tenancy boundary
by the detail read.

**Coverage: the denominator moved.** The prefix-based Design A sweep only
considered `/v1/provider|staff|tenant/*`, so three genuine tenant mutations on
`/v1/reviews/*` had never been counted. 226 -> 229 denominator, 209 -> 212
numerator, 17 unprotected (unchanged). This slice's 209/226 was therefore
*incomplete*, not incorrect -- and the same generic-prefix blind spot may
exist in other engines, recorded as an open coverage-completeness caveat.

This slice's canonical closure is re-asserted intact by test
(`test_canonical_customer_reviews_closure_intact`).

Note for readers comparing regression figures: the API server, PostgreSQL and
Redis became reachable during 2F-25, resolving 79 failures and all 111 errors
environmentally. Neither slice caused that; 2F-25's report leads with the
correction.

Final status for 2F-25:
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`.
See `../phase-02a-slice-02f25/approval-gate.md`.
