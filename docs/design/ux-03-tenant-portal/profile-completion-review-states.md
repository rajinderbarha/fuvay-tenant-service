# Profile Completion / Review States

One centralized component, `ReviewStateBanner`
(`components/ux03/widgets/ReviewStateBanner.tsx`), renders all 9 states:
`not_started`, `in_progress`, `ready_to_submit`, `submitted`,
`under_review`, `changes_requested`, `approved`, `rejected`, `suspended` —
reused by the dashboard, business profile, and setup wizard rather than
each implementing its own banner. `changes_requested` additionally renders
the specific change list (`TenantProfileFixture.changesRequested`).
