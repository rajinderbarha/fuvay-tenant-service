# Service-Layer Ownership Report

## Methods audited this slice

| Method | Callers | Ownership before | Ownership after |
|---|---|---|---|
| `create_job` | `create_job` route, `_spawn_repair_from_consultation` (internal) | `tenant_id` accepted as-is from caller | tenant-scoped roles pinned to `actor_tenant_id` (fixed) |
| `convert_to_repair` | `convert_to_repair` route | `_get_job_for_assignment` (already correct) | unchanged |
| `spawn_repair_from_consultation` | `spawn_repair` route | **none at all** | `_get_job_for_assignment` + duplicate-repair guard (fixed) |
| `create_quote` | `create_quote` route | **none at all** | `_get_job_for_quote_management` (fixed) |
| `_get_job_for_quote_management` | `create_job_quote`, `send_job_quote`, `create_quote` | never denied `customer` | explicit customer denial (fixed) |
| `respond_to_quote` | `respond_to_quote` route | `quote.customer_id == customer_id` (correct, but `customer_id` itself could be spoofed at the router) | unchanged at service layer; router now guarantees `customer_id` is authentic (fixed) |
| `approve_job_quote`/`reject_job_quote` | respective routes | `_get_quote_for_customer` (already correct) | unchanged |

## Conclusion

A stronger API caller did not conceal a weaker one in most of this surface — the pattern found
was the opposite: the router layer was uniformly weak (`get_current_user` only, or a
client-trusted `tenant_id`/`customer_id`), while the service layer was a mix of correct
(`convert_to_repair`, `approve_job_quote`/`reject_job_quote`) and genuinely absent
(`spawn_repair_from_consultation`, `create_quote`, and the customer-denial gap in
`_get_job_for_quote_management`). All identified gaps are closed. No further directly-connected
bypass was found in this audit.
