# Operational Exception Pattern

Built: type `OperationalExceptionView`/`OperationalExceptionKind`
(`lib/ux04/types.ts`), component `components/ux04/OperationalRiskBanner.tsx`
(no showcase route wires it in yet — component exists and renders from a
literal prop, verified by inspection, not yet embedded in a page).

11 kinds modeled per brief: `no_technician_available |
outside_service_area | invalid_price_config | missing_quote |
parts_unavailable | low_credit | incomplete_checklist | invalid_transition
| missing_customer_confirmation | compliance_restriction |
security_contract_blocked`. Deliberately **not** an active Booking
Exception Resolution engine — the component only renders explanation,
affected workflow, safe actions, and an optional escalation path; there is
no "resolve" button anywhere in the component or type.
