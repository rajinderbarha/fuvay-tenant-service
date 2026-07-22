# Action Conflict Report — Slice 2F-26H

When the strongest evidence level yields more than one distinct action, the
model returns `REQUIRES_MANUAL_ACTION_ADJUDICATION` with the competing evidence
recorded in `rejected` and the reason in `conflict`. Example:
`service_methods=("approve_thing","delete_thing")` → conflict (approve vs
delete) → MANUAL. No unresolved conflict was silently resolved on the fifth
holdout; no conflict contributed to any canonical decision.
