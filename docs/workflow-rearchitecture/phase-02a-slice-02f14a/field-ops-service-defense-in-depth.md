# field_ops Service-Layer Defense in Depth

## Methods audited this slice (in addition to Slice 2F-14's audit)

| Method | Callers | Ownership | Notes |
|---|---|---|---|
| `start_assessment` | staff_router (none — not mounted there), field_ops.router | `_get_job_for_staff_action` | now also role-gated at router (fixed) |
| `complete_assessment` | field_ops.router | `_get_job_for_staff_action` | now also role-gated at router (fixed) |
| `void_job` | field_ops.router | previously NONE; now `_get_job_for_assignment` (fixed) | genuine cross-tenant IDOR closed |
| `add_note` | field_ops.router | previously NONE; now `_assert_can_access_job` + customer denial (fixed) | tenant_id no longer client-supplied |
| `list_notes` | field_ops.router | previously NONE; now `_assert_can_access_job` + is_internal filter (fixed) | |
| `add_media` | field_ops.router | previously NONE; now `_assert_can_access_job` + customer denial (fixed) | tenant_id no longer client-supplied |
| `list_media` | field_ops.router | previously NONE; now `_assert_can_access_job` (fixed) | no is_internal-equivalent exists |
| `close_job_financial`/`generate_invoice`/`record_payment`/`deduct_commission`/`financial_close` | field_ops.router (via BillingService) | `_get_job_for_billing` (already correct, unmodified) | router guard upgraded (fixed) |
| `create_job_quote`/`send_job_quote` | field_ops.router | `_get_job_for_quote_management` (already correct, unmodified) | not fixed — distinct capability, ownership already present |
| `approve_job_quote`/`reject_job_quote` | field_ops.router | `_get_quote_for_customer` (already correct, unmodified) | not fixed — distinct capability, ownership already present |
| `respond_to_quote` | field_ops.router | `quote.customer_id != customer_id` check (already correct, unmodified) | see product-decisions-required.md re: non-customer callers supplying an arbitrary `customer_id` |

## Conclusion

A strong router (`field_ops.router`'s permission/role dependencies) was concealing three weaker
service-layer callers this slice: `void_job` (no ownership at all), `add_note`/`list_notes`,
`add_media`/`list_media` (no ownership at all, client-supplied `tenant_id`). All three are fixed.
`create_job_quote`/`send_job_quote`/`approve_job_quote`/`reject_job_quote`/`respond_to_quote`
already had correct or partially-correct service-layer ownership checks and were not modified —
classified as distinct capability, not touched per the mission's scope discipline.
