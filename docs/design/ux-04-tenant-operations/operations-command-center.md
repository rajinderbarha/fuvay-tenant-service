# Operations Command Center

Built: `app/dev/ux-04/command-center/page.tsx`, component
`components/ux04/OperationalActionQueue.tsx`, fixture `actionQueueFixture`.

One composition renders for every canonical role — `tenant_owner`,
`staff` with operations permission, `staff` limited, and read-only. The
only variable is which `ActionPermissionView.available` entries are true
per item; when none are, the queue item still renders (so nothing
disappears from view) but shows "No action available with your current
permissions" instead of a control. This is the pattern every future
role-sensitive operations page should follow — never fork into
role-specific components.

Sections specified but not built this pass (fixtures/types ready, no
route): Today summary strip, dispatch overview panel, financial alerts
panel (low credit / insufficient credit), compliance/support alerts panel.
`OperationalActionItemView` already carries enough shape (`entity`, `sla`,
`requiredAction`) to compose these directly from the same queue data —
deferred for time, not blocked technically.
