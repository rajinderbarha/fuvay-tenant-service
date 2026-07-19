# Read-Only Operations Mode (DEFERRED — no dedicated route)

Not built as a separate showcase route this pass. The pattern already
exists in every built component: `PartsRequestSummary` and
`OperationalActionQueue` both render an explanatory message instead of a
control when the relevant `ActionPermissionView.available` is false,
rather than showing a disabled-but-visible fake button. A dedicated
"read-only operations" showcase would apply the same `available: false`
treatment across every action in `JobDetailView`/`BookingListItemView`
simultaneously — no new component work required, just a fixture variant
and a route, both deferred for time.
