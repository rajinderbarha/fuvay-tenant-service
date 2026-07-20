# Approval Gate — Slice 2F-10

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**
**[CORRECTED IN SLICE 2F-10A]:** This slice's own text honestly flagged
3 unresolved domain-integrity questions (`create_complaint`'s incomplete
eligibility enforcement, `check_eligible`'s unclear advisory/authoritative
status, and `create_refund_request_from_complaint`'s unproven silent
no-op behavior) while still claiming `DOMAIN_INTEGRITY ... CLOSED` in the
combined status string — that combination was unsupportable, the same
class of error Slice 2F-9A corrected in Slice 2F-9's documentation.
Slice 2F-10A resolved all 3: `check_eligible` is classified
CANONICAL_CREATION_POLICY and is now actually enforced by
`create_complaint` (previously bypassed for status/window/duplicate
rules); the refund silent-transition behavior was proven, not assumed,
to be deliberate and correct. See
`phase-02a-slice-02f10a/approval-gate.md` for the verified final answer.
Everything else in this document (security/IDOR/privacy/settlement
findings) remains accurate and unmodified.

## Reasoning

### SECURITY_CLOSED: YES
Fresh runtime introspection (not assumed from the provider slice) found
all 15 mounted `complaints.customer_router` routes using
`get_current_user` only — no role check at all, independently confirming
the mission's warning that this router "may have a structurally similar
gap." Fixed by applying the pre-existing, already-used-elsewhere
`require_customer` dependency to all 15 routes. Three genuine,
directly-connected ownership bypasses were found and fixed:
1. `create_complaint` had zero record-ownership check (any authenticated
   caller could file a complaint against any booking/job/etc by ID).
2. `create_refund_request_from_complaint` had zero complaint-ownership
   check (bare fetch-by-id, unlike every other customer route).
3. `_get_resolution` had no complaint cross-check (foreign
   resolution_id accept/reject), the identical bug class Slice 2F-9 fixed
   for settlement proposals.
`_get_settlement_proposal`'s cross-check was re-verified as already
correctly closed (shared method, fixed once in Slice 2F-9, benefiting
both routers). No weaker alternate route was found for any customer
capability (`alternate-customer-complaint-route-audit.md`). Zero
unverified routes remain — runtime inventory confirms 8/8 mutation routes
verified, 0 unverified.

### DOMAIN_INTEGRITY_CLOSED: YES
Complaint state transitions for every customer mutation were traced
against the actual `ALLOWED_TRANSITIONS_EXT` map (re-extracted fresh, not
assumed from 2F-9A). An ordering defect was found and fixed:
`customer_accept_resolution`/`customer_reject_resolution` mutated
`resolution.status` — and, for a rework resolution, created and
**committed** a real `ServiceReworkRequest` — before validating the
complaint's transition legality. Fixed by pre-validating via
`ALLOWED_TRANSITIONS_EXT` before any mutation, proven directly via tests
that assert `db.flush`/`db.commit` are never called and
`ServiceReworkService` is never instantiated on an illegal-state attempt.
Repeated final decisions are rejected (not idempotent, correctly
classified as `STATE_TRANSITION_REJECTED`). Dual-acceptance settlement
behavior, monetary-remedy blocking, and rework/refund boundary separation
all remain intact and unmodified. No confirmed integrity defect remains
open.

### PRIVACY_CLOSED: YES
Customer reads are filtered server-side by `customer_id` (list) and
`get_customer_complaint`'s ownership check (detail/messages/resolutions/
settlement-proposals/AI-session) — all pre-existing, re-verified
unmodified. Message visibility (`is_visible_to`) correctly restricts
customer reads to `public_to_case`/`customer_only` content, hiding
provider-internal/platform-only messages. No foreign complaint/resolution
ID leaks existence information (uniform not-found error codes, verified
directly for the newly-fixed `_get_resolution` cross-check). No
customer-facing evidence/rework-status read route exists at all —
reported as absent, not silently claimed private-but-working.

### PRODUCT_POLICY_CLOSED: BLOCKED
Two carried-over/parallel product questions remain open and undecided
(see `product-decisions-required.md`): whether
`add_customer_message`/`create_refund_request_from_complaint` should
enforce additional policy (resolved/settled blocking; illegal-transition
raising instead of silent no-op) beyond what this slice's
conclusively-provable fixes required. Neither blocks security, domain
integrity, or privacy closure.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Quality gates (48) — summary
All satisfied and verified directly, not asserted — evidence distributed
across the other 24 files in this directory. Notable direct proofs:
role-gate HTTP tests (25 new tests), 3 service-layer IDOR fixes each with
a dedicated direct test, the ordering-defect fix proven via mock
call-count assertions, runtime inventory exit 0 for both customer and
provider routers, and a full targeted + broader regression run (139 +
342 passed, 0 new failures; pre-existing live-DB-only failures separately
documented and excluded from the pass count with full transparency).

## Global coverage
106/182 unchanged — customer self-service routes were never part of that
tenant-mutation denominator and are not added to it now (see
`global-coverage-update.md`). Customer router's own coverage: 8/8
mutation routes now verified (was 0/8).

## Stop condition honored
Only `complaints.customer_router`, `complaint_service.py`,
`refund_service.py`, and the mutation-inventory tool (a shared,
general-purpose classification extension, not a router change) were
modified. `complaints.provider_router` and `complaints.admin_router` were
not modified — the one shared method touched
(`_get_settlement_proposal`) required no further change, having already
been fixed by Slice 2F-9 to close both callers at once; nothing new was
done to it this slice. `execution.real_estate_router`,
`execution.coaching_router` were not begun. No permission was granted; no
new role was introduced (`customer` and `require_customer` both
pre-existed). No visual redesign occurred — no frontend file was
modified at all. `readonly@demo-ac-services.local` and migration 144 were
untouched. The booking-pipeline architecture question remains unresolved
and unmerged. **Stopping here per instruction — not beginning another
router module.**
