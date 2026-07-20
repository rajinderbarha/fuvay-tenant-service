# Service Detail Visual Audit — UX-06 Round 5 (Workstream 7)

**Built this round — did not exist before.** New screen
`src/screens/ServiceDetailScreen.tsx`, registered as a real stack route
(`ServiceDetail`) in `AppNavigator.tsx`, reachable from a real "Details ⓘ"
link on each offering row inside the chat booking flow (production nav, not
a dev showcase).

Real data only: `GET /v1/customer/categories/{category_slug}/offerings/{offering_slug}`
(confirmed real this round). Shows: name, category, description, starting
price (or an honest "shown after checking your area" fallback when absent),
visit fee if any, a plain-language "what we need from you" list derived from
the real `requires_brand`/`requires_type`/`requires_address`/`requires_slot`
flags (never raw field names), the standard on-site-payment note, and a
"Book via Chat" primary action. Loading (skeleton) and error states are real,
designed (not default RN activity spinners). No raw JSON, no internal IDs as
primary labels, no dev readiness text.

Not verified this round: 320px width, large-text/accessibility scaling, an
explicit offline state (see known-limitations.md).
