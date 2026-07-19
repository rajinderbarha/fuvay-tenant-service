# Operational Exception Pattern (UX-04A)

`OperationalRiskBanner` (built at UX-04 baseline, unembedded then) is now
embedded in a real route: `/dev/ux-04/operational-exceptions`, with 3
fixture exceptions (`no_technician_available`, `low_credit`,
`invalid_transition`). Route description explicitly states this is NOT the
blocked Booking Exception Resolution engine — the component renders
explanation/safe-actions/escalation only, no "resolve" control exists in
its source.
