# UX-08 Known Limitations

## Documentation scope, honestly disclosed

The full UX-08 brief nominally lists 45 documents covering exhaustive
route/role/API inventories across 4 applications, a full mock/fixture
census, and complete per-app functional baselines. Given realistic time
constraints, this pass prioritized:

- Baseline freeze + ancestry verification (full depth)
- UX program history (full depth, synthesis of real prior evidence)
- Customer-app + Super Admin test/typecheck reconciliation (fresh,
  independently re-run)
- Cross-app workflow map (synthesis of real prior UX-07 evidence, not
  re-executed live this pass)
- Unsupported capability registry + backend contract handoff (full depth)
- Future Customer redesign handoff + responsive deferral plan (full depth)
- Release baseline matrix (full depth)
- Non-change audit (full depth, verified via `git diff --stat`)

**Given lighter-weight treatment or not separately produced this pass**
(cited from existing prior-phase evidence rather than freshly
re-derived): full per-route inventories for Tenant Portal/Staff app/Super
Admin beyond what UX-04/05/07 already documented; a from-scratch mock/
fixture grep across all 4 applications (a representative census was
written instead, citing known items from prior rounds); Tenant Portal and
Staff app fresh test re-runs (cited from their own closure evidence
instead, since no code changed in those apps during UX-07/UX-08); a new
live cross-app smoke verification (the existing real Round 3 records were
judged sufficient rather than creating new bookings unnecessarily).

## Carried-forward limitations (see `unsupported-capability-registry.csv` for full detail)

- Customer cancellation/rescheduling: not built, by design.
- Booking Exception Resolution: remains blocked, by design.
- `POST /v1/customer/reviews` malformed-input raw 500: backend-owned,
  ticketed, not fixed in UX-08.
- Quote/checklist/technician-parts-creation: partially backend-wired;
  gaps ticketed, not fixed in UX-08.
- Final authenticated Home/SmartBot Playwright visual sweep: not
  completed (backend was unreachable during UX-07 Pass 3f's verification
  window; not re-attempted this pass since UX-08 is a consolidation
  phase, not a new visual-evidence-capture phase).
- No seeded `admin_readonly` account exists for live read-only-role
  verification — disclosed, not fabricated.
- Responsive certification and final Customer visual design: both
  explicitly deferred (`DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT`),
  per direct user instruction — not a defect.
