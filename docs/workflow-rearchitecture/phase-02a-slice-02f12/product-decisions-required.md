# Product Decisions Required — Slice 2F-12

1. **Should `cancel_appointment` be assignment-limited, matching the
   other 7 mutations?** Currently any authorized tenant_owner/staff (not
   only the assigned one) may cancel — an intentional-looking business
   design (front-desk/manager cancellation authority), but not
   conclusively confirmed as deliberate versus an oversight in the
   original Sprint 21 implementation. Not changed this slice — the
   persona-layer fix (excluding technician/unauthorized roles) already
   closes the security-relevant gap regardless of this open question.

2. **Should `is_customer_visible` note creation be independently
   permission-gated?** No evidence found either way — not changed
   (carried over from the identical real-estate question).

3. **`app.engines.coaching_appointment`'s own architecture and
   authorization strength** — inspected and classified
   (`DISTINCT_MODEL_DISTINCT_CAPABILITY`), but not independently
   hardened or re-audited; flagged as a candidate for a future dedicated
   slice if ever brought into scope.

4. **Whether this module's execution capability should ever expand into
   full slot-hold/enrolment/conversion management** — explicitly out of
   scope for this slice, a future product-roadmap decision.
