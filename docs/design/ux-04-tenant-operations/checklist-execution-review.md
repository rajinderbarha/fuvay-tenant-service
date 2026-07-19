# Checklist Execution + Review

Built: `components/ux04/ChecklistProgress.tsx`, type `ChecklistView` /
`ChecklistSectionView` / `ChecklistItemView`. One component, three modes
via the `mode` prop: `"technician_execution"` (all notes visible, no
reviewer note), `"provider_review"` (adds reviewer note), and
`"customer_summary"` (filters to `customerVisible` items only, strips all
internal notes — used to guarantee internal checklist notes never leak to
a customer-facing render).

Job Detail Workspace renders it in `"provider_review"` mode. No dedicated
`technician_execution` or `customer_summary` showcase route was built this
pass (same component, different `mode` prop — a one-line addition per
route). Completion-lock (`completionLocked`) is rendered as a warning
banner; no actual lock/validation logic is wired (read-only showcase).
