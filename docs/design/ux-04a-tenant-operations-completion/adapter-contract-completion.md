# Adapter Contract Completion

No change to `Ux04OperationsAdapter` (`lib/ux04/types.ts`) this pass — all
method signatures from UX-04 baseline are unchanged and now have fixture
data for every method's return type (inspection, complaint, dispute,
operational exceptions, SLA gallery added this pass). Per-method
route/shape/permission/error-mapping documentation (the gap noted in
UX-04's `frontend-adapter-contract.md`) remains **not written out** this
pass — still only TypeScript signatures + `OperationalViewMeta` envelope.
Carried forward as a real, unresolved gap — see `deferred-items.md`.
