# Deferred Items

Deferred to a follow-up pass (types/fixtures largely ready, no route/UI
built): booking detail (both pipelines), field_ops.Job detail variant,
standalone status-transition/quote/checklist/credit-commission/customer-
communication routes (currently only shown inline inside Job Detail
Workspace), inspection workflow, checklist technician-execution +
customer-summary modes as separate routes, parts list (non-approval
variant), invoice/payment standalone route, complaint list/detail,
dispute, compliance submission route, media gallery (`EvidenceGallery`
component), SLA-risk states gallery, operational exceptions gallery
(`OperationalRiskBanner` built but unembedded), staff operational home,
read-only operations mode, restricted-action-states gallery, operational
search (adapter method + UI), automated test suite, per-adapter-method
contract documentation table.

None of these are blocked by a product/security decision except where
noted in `product-decisions-required.md` — they are straightforward
composition work on top of the types/fixtures/components already built.
