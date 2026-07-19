# Read-Only / Restricted Action States (UX-04A)

New route `/dev/ux-04/read-only`, reusing `PartsRequestSummary` with every
`ActionPermissionView.available` forced `false` and a "Read-only mode — no
mutation permitted" reason. Demonstrates, in one page, both original items
26 (read-only operations) and 27 (restricted-action states) — the same
underlying pattern (`available: false` -> explanatory text instead of a
control) already used at baseline in `PartsRequestSummary` and
`OperationalActionQueue`, now shown as a dedicated example rather than
only incidentally.
