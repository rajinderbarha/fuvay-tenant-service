# Documentation Corrections

## Slice 2F-6A's implicit claim never propagated to the canonical CSV
Slice 2F-6A fixed `provider_issue_invoice`, `provider_record_payment`, `staff_create_invoice`, and `staff_add_invoice_item` (`app.engines.invoice_payment.provider_router`), but the canonical `tenant-mutation-endpoint-inventory.csv` rows for these 4 routes were never updated — they remained marked `UNVERIFIED` for at least 11 subsequent slices (2F-7 through 2F-16A), silently understating the true canonical protected count by 4 the entire time. Corrected this slice — see `coverage-row-diff.csv`.

## Slice 2F-2's `preview_matching_inputs` false-positive exemption never propagated to the canonical CSV
Slice 2F-2 added `preview_matching_inputs` to the runtime tool's `CONFIRMED_FALSE_POSITIVE_ROUTES` set, but the canonical CSV row was never removed — it remained counted in the tenant denominator (as an unprotected row) for the same span. Corrected this slice.

## No prior slice's approval-gate claims are reversed
Both corrections are bookkeeping/CSV-staleness fixes, not reversals of any prior slice's security work — the underlying code was already correct at the time each prior slice claimed it (2F-2 and 2F-6A respectively); only the CANONICAL CSV's bookkeeping lagged behind.

## This slice does not correct any 2F-16/2F-16A claim
Both prior slices' approval-gate claims (quote-checklist and invoice-lineage closure) remain fully accurate and unqualified by this slice — the 186/227 baseline they reported was itself correct at the time; this slice's reconciliation is a SEPARATE, unrelated bookkeeping correction to OTHER modules' stale rows that happened to be counted within the same CSV.
