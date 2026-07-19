# Dispute Presentation (type built, showcase route DEFERRED)

Type: `DisputeView` (`lib/ux04/types.ts`) — `id`, `customerId`,
`relatedEntity`, `amountContextLabel`, `reason`, `evidence`, `status`
(`open | under_platform_review | decided`), `tenantResponse`, `timeline`,
`decision`. Comment on the type explicitly preserves: platform issues a
Customer Service Credit (never a cash refund), and tenant credit is
deducted per policy (never presented as a tenant payout). No showcase
route built this pass; no fixture data written for this type yet.
