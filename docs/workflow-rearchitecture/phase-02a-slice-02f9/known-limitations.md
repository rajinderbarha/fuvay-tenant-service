# Known Limitations — Slice 2F-9

1. **[CORRECTED IN SLICE 2F-9A] No final-state check on
   `respond_to_complaint`/`offer_resolution`.** This item was only half
   right. Direct source re-reading in Slice 2F-9A proved
   `provider_offer_resolution` was ALREADY fully protected via the
   pre-existing `_transition`/`ALLOWED_TRANSITIONS_EXT` mechanism — no
   code fix was needed there, only direct tests proving it (see
   `phase-02a-slice-02f9a/resolution-offer-state-behavior.md`).
   `provider_add_response` genuinely lacked any final-state check; this
   was fixed in Slice 2F-9A by adding the same `FINAL_STATUSES` guard its
   own customer-side sibling method already used. See
   `phase-02a-slice-02f9a/provider-response-state-behavior.md`.

2. **`complaints.customer_router` shows the same surface-level
   authorization gap** (no permission/role guard) this slice fixed for
   the provider router. Not audited or modified — a distinct module
   boundary, strongly recommended as the next slice.

3. **`AddMessageIn.visibility` is dead input** — the schema accepts it
   but the service always hardcodes `public_to_case`. No provider-
   internal-note capability actually exists. Documented, not built.

4. **[CORRECTED IN SLICE 2F-9A] No audit event for
   `provider_add_response`.** This claim was factually wrong. Direct
   source re-reading in Slice 2F-9A proved `provider_add_response`
   already calls `self._log_event(..., EVT_PROVIDER_RESPONDED, ...)`,
   writing a `ComplaintEvent` row identically to the other 8 mutation
   paths. No audit gap ever existed. See
   `phase-02a-slice-02f9a/audit-event-resolution.md`.

5. **No duplicate-proposal guard on `create_settlement_proposal`** —
   multiple proposals per complaint appear intentional (a normal
   negotiation pattern), not conclusively a defect.

6. **Rework creation and admin-approval, and refund admin-approval,
   ownership were not located or audited** — these methods exist in the
   service layer but are not reachable from `provider_router.py`; their
   own router (if any) was not identified this slice.

7. **Frontend fix scoped to one page.** Only
   `complaints/[complaint_id]/page.tsx`'s 4 mutation controls were
   corrected. `refund-requests/page.tsx` was confirmed read-only (no fix
   needed); no rework-requests page was found to exist at all.

8. **Frontend lint not verified** — pre-existing environment/tooling
   gap, documented, not silently skipped.

9. **Product-policy questions left open by design**: whether staff
   should ever get delegated complaint-response capability, and whether
   `complaints.customer_router` needs the same closure — both
   deliberate, policy-driven non-closures, not oversights.
