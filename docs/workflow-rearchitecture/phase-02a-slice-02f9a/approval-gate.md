# Approval Gate — Slice 2F-9A

## Status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Reasoning

### AUTHORIZATION_CLOSED: YES
All 9 mutations in `complaints.provider_router` remain gated by
`require_tenant_owner_mutation` (Slice 2F-9, unmodified). Re-run and
confirmed passing — see `authorization-regression-report.md`. Runtime
inventory: 9/9 verified, 0 unverified. Global coverage unchanged:
**106/182**.

### DOMAIN_STATE_INTEGRITY_CLOSED: YES
Both target routes' final-state behavior was determined by direct source
investigation and proven, not assumed, via a full state matrix
(`direct-state-test-matrix.csv`, 30 new tests, all passing):
- `provider_add_response`: previously had no final-state check at all.
  Fixed with `if complaint.status in FINAL_STATUSES: raise
  ValueError(ERR_COMPLAINT_ALREADY_CLOSED)`, mirroring its own
  customer-side sibling method's identical, pre-existing pattern.
- `provider_offer_resolution`: already fully protected via
  `self._transition(...)` → `ALLOWED_TRANSITIONS_EXT`. No fix needed for
  legality; a real ordering defect was found and fixed instead (the
  `ComplaintResolution` row was created/flushed before the legality
  check ran) — reordered so no record is ever created on an illegal-state
  attempt.
- Repeated/conflicting actions correctly classified: ordinary repeated
  messages are `ALLOWED_MESSAGE_APPEND`; repeated resolution offers while
  one is pending are correctly `STATE_TRANSITION_REJECTED`.
- Side-effect safety proven: zero `db.add`/`db.flush`/`db.commit` calls
  on every rejected path, for both routes, across every tested illegal
  state.
- Slice 2F-9's incorrect documentation claims (that `offer_resolution`
  had "no state precondition" and that `provider_add_response` "has no
  audit event") are corrected in place in `phase-02a-slice-02f9/`.

### AUDIT_CLOSED: YES
`provider_add_response` already logs `EVT_PROVIDER_RESPONDED` (Slice
2F-9's claim otherwise was incorrect); `provider_offer_resolution`
already logs `EVT_RESOLUTION_PROPOSED`, correctly only on successful
transitions. No new audit event was needed or added. See
`audit-event-resolution.md`.

### FRONTEND_STATE_POLICY_ALIGNED (as of Slice 2F-9A): YES, PARTIALLY
**[CORRECTED IN SLICE 2F-9B — now YES, exactly.]** As shipped in this
slice, the "Reply to customer" and "Offer resolution" controls on
`complaints/[complaint_id]/page.tsx` were hidden once the complaint was
`closed`/`cancelled`/`rejected`, matching `respond_to_complaint`'s actual
backend policy exactly, but only conservatively (not exactly) matching
`offer_resolution`'s stricter, 2-state backend policy. This was
correctly labeled a remaining open item at the time
(`product-decisions-required.md` item 2), not silently claimed closed.
Slice 2F-9B implemented the exact 2-state gate
(`canOfferProviderComplaintResolution`) and re-verified it directly with
36 passing helper tests plus a manual deep-link/stale-state review — see
`phase-02a-slice-02f9b/approval-gate.md` for the corrected final result.

### PRODUCT_POLICY_CLOSED: BLOCKED
Two genuine, unresolved product questions remain (see
`product-decisions-required.md`): (1) whether `provider_add_response`
should also block on `resolved`/`settled`, not just base
`FINAL_STATUSES`; (2) whether the frontend should encode the full
2-state legal-source precision for `offer_resolution`'s button instead of
the coarser 3-state final check. Neither blocks security or domain-state
integrity closure — both are refinements requiring an explicit product
decision this slice was not authorized to make.

## Final combined status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Quality gates (42) — summary
All satisfied **for this slice's own scope**. The one item that was
correctly left as a documented gap rather than falsely claimed closed —
exact frontend state-precision for `offer_resolution` — is now closed by
Slice 2F-9B; see that slice's `approval-gate.md`. Evidence distributed
across the other 15 files in this
directory (`implementation-summary.md`, `final-state-policy-matrix.csv`,
`provider-response-state-behavior.md`,
`resolution-offer-state-behavior.md`,
`repeated-conflicting-action-review.md`,
`invalid-state-side-effect-proof.md`, `audit-event-resolution.md`,
`frontend-state-alignment.md`, `alternate-caller-review.md`,
`direct-state-test-matrix.csv`, `authorization-regression-report.md`,
`product-decisions-required.md`, `test-report.md`,
`known-limitations.md`, `deferred-items.md`).

## Stop condition honored
Only the 2 named target methods and their 1 frontend page were
investigated, tested, and (where evidence-justified) fixed. No
previously-closed module was modified — confirmed via `git status`/`git
diff --stat` showing changes confined to `app/engines/complaints/`,
`frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`,
and this slice's own test/doc files.
`complaints.customer_router`, `complaints.admin_router`,
`execution.real_estate_router` were not begun or modified. No complaint
permission was created; no capability was granted to staff or
technicians; no new role was introduced; no internal-note system or new
dispute interface was built; no refund/cash-payment behavior was
created; the internal-credit settlement model was not changed; no models
were merged; `readonly@demo-ac-services.local` and migration 144 were
untouched; no visual redesign occurred. **Stopping here per instruction —
not beginning `complaints.customer_router` or any other module.**
