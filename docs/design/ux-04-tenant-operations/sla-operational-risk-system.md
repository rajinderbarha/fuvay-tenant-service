# SLA / Operational Risk System

Built: type `SLAState`/`SLAStateView` (`lib/ux04/types.ts`), component
`components/ux04/SLAIndicator.tsx`, used in the Command Center action
queue and the Booking+Job List showcase.

States: `on_track | approaching_deadline | at_risk | breached | blocked |
waiting_on_customer | waiting_on_provider | waiting_on_platform |
product_decision_blocked`. Every value in `lib/ux04/fixtures.ts` is a typed
fixture value with an explicit `explanation` string (shown as a tooltip on
hover) — no calculation rule is implemented client-side (e.g. no "SLA
breaches after N hours" logic lives in the frontend). Detail-page
inline explanation and dashboard-alert composition (beyond the badge
itself) are demonstrated via the Command Center queue but there's no
standalone "SLA-risk gallery" showcase route enumerating all 9 states.
