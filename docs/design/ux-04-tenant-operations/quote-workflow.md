# Quote Workflow

Built: `components/ux04/QuoteSummary.tsx` used in Job Detail Workspace.
Type `QuoteView`/`QuoteLineItemView`. Statuses modeled: `draft | submitted
| awaiting_customer | approved | rejected | revised` (`expired`/`cancelled`
omitted — brief marks them "if-real"; not confirmed against a real
backend enum this pass, so left out rather than fabricated).

Line items typed by kind (`labor | parts | addon | fee | discount`);
subtotal/total come from the adapter/fixture directly, never recomputed
client-side beyond what's already provided. Revision number, created-by,
customer response, and timeline are all rendered in `QuoteSummary`. No
standalone Quote Workflow showcase route exists separately from Job Detail
Workspace this pass.
