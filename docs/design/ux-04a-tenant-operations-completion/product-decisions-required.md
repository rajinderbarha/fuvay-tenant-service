# Product Decisions Required (UX-04A)

Carries forward UX-04's 6 open items (unchanged, see UX-04's own
`product-decisions-required.md`), plus:

7. **ServiceBooking pipeline identity** — should UX-03's fixture layer gain
   a distinct `ServiceBookingFixture` type separate from `ServiceJobFixture`,
   or is representing the pre-job ServiceBooking state as a
   job-specific-sections-hidden view of `ServiceJobFixture` (this pass's
   approach) the intended long-term model? See
   `booking-detail-pipeline-evidence.md`.
8. **UX-03 test suite hook-call failure** — root cause not diagnosed this
   pass (`PermissionEditor.test.tsx`, `SetupWizard.test.tsx`); needs a
   dedicated investigation, potentially a React/testing-library version
   pin decision.
9. **Compliance submission resubmission flow** — `ComplianceSubmissionView`'s
   extension fields (`affectedFields`, `resubmissionSupported`, etc.) have
   no UI yet; product should confirm whether UX-03's existing compliance
   page is the intended long-term home for this or whether a dedicated
   UX-04-style workflow is wanted.
