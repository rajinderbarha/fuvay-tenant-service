# Dispute Presentation (UX-04A)

New: `DisputePresentation` (`components/ux04/ComplaintWorkspace.tsx`),
fixture `disputeFixture`, same route as complaints
(`/dev/ux-04/complaints`). Explicitly states the platform issues a
Customer Service Credit, never a cash refund, and tenant credit is
deducted per policy. `ComplaintWorkspace.test.tsx` asserts this exact copy
renders and that the component renders zero buttons — no platform-only
resolution control is ever exposed to the tenant.
