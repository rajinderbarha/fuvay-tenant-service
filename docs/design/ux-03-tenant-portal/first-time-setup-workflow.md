# First-Time Setup Workflow

Canonical stages (implemented in `/dev/ux-03/setup-wizard` via
`components/ux03/patterns/SetupWizard.tsx`): account created -> business
profile -> registration/tax -> owner info -> address -> service categories
-> service areas -> team setup (optional) -> package/deposit requirements
-> review summary -> submit -> under review -> approved / rejected /
changes-requested.

Save/resume: each `goNext()` call invokes `onSaveDraft(stepId)` — a stub in
the showcase, a real draft-persistence call once
`API_CONTRACT_REQUIRED` is resolved. Progress indicator shows `step index /
total` and a percentage bar. Blocked steps (`WizardStep.blocked`) render
disabled in the step nav; optional steps are labeled "(optional)" and never
block progression.
