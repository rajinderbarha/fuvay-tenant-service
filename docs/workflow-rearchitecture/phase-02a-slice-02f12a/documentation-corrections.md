# Documentation Corrections — Slice 2F-12A (Workstream 14)

## Slice 2F-12 files corrected

### `approval-gate.md`
- **`SECURITY_CLOSED: YES`** header annotated: the 2F-12 claim of full
  security closure was ahead of its evidence for `cancel_appointment` —
  only the router guard and tenant ownership were proven for cancel; the
  same-tenant staff *object* authority was left unverified. Now resolved
  in 2F-12A.
- **`cancel_appointment` non-assignment-limited design** paragraph
  corrected: was "documented, not treated as a defect" (implying
  intentional but leaving it UNVERIFIED); now points to 2F-12A's
  verification via the approved 2F-3B sibling `cancel_job`
  ("tenant-wide provider action").
- **Quality gates (57) summary** corrected: the one gate covering
  cancel's object authority was labeled satisfied but was actually
  unverified at 2F-12 time; now genuinely closed by 2F-12A.

## What was NOT changed (preserved, per the mission)
- Architecture classification (CoachingAppointment execution/CRM tracker).
- The seven assignment-limited mutation findings.
- Read/privacy closure.
- State-machine integrity findings.
- `app.engines.coaching_appointment` alternate-module classification.
- Global coverage of 125/182.
- Slice 2F-12's `consultation-session-state-machine.md` and
  `known-limitations.md` cancellation notes were left as historical
  record (they correctly flagged the question as open/product-decision);
  this slice's own docs carry the corrected, verified answer forward
  rather than rewriting every prior mention. The overall combined status
  label (`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`)
  remains correct and unchanged.
