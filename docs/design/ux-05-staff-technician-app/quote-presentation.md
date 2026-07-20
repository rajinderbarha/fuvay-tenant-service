# Quote Presentation

Checked `src/lib/api.ts` in full before building anything: **no `quoteApi`, no quote field on `Job`/`JobDetail`/
`ExecutionEvent`, nothing quote-related exists anywhere in the real API client.** This workstream is entirely
`api_contract_required` / `mock_design_only`.

`QuoteShowcaseScreen` renders a read-only presentation of a fixture `QuoteSummaryView` — status label, line-items
summary, and two capability flags (`technicianCanEdit`, `staffCanReview`) shown as plain text, not interactive
controls, since there is nothing real to submit to. No "Approve"/"Finalize Price"/"Record Customer Approval"
action exists anywhere in the view model or the screen — that authority stays with the customer/platform per the
hard constraint, enforced by omission rather than a runtime check.
