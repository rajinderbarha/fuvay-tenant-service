# Route Resolution Report — Slice 2F-39A4

All 21 routes flagged `PRODUCT_DECISION_REQUIRED` by Slice 2F-39A3 were
individually service-layer traced (fully qualified route identity: module +
endpoint function + HTTP method + mounted path), per the reviewer's required
bar for closing such a row. Outcome per route:

## 9 confirmed real authorization defects — fixed

| # | Route (module::function) | Defect | Fix |
|---|---|---|---|
| 1 | `service_catalog.router::deactivate_item` `POST /v1/catalog/items/{item_id}/deactivate` | Zero tenant scoping — service method had no ownership check at all, unlike sibling `update_item` in the same file | Added the identical `actor_tenant_id == item.tenant_id` check (non-oracular `NotFoundException` on mismatch); router guard → `require_tenant_mutation_permission` |
| 2 | `inventory.router::replenish` `POST /v1/inventory/tenants/{tenant_id}/items/{item_id}/replenish` | `request_replenishment` was the only mutation in `InventoryService` skipping the existing `_require_trusted_tenant` helper every other sibling calls | Added `_require_trusted_tenant(tenant_id)` call; router guard → `require_tenant_mutation_permission` |
| 3 | `notification.router::test_channel` `POST /v1/notifications/tenants/{tenant_id}/channels/{channel}/test` | Zero tenant scoping (no persistent write, but a cross-tenant probe/leak) while sibling `set_channel_config` already uses `_require_trusted_tenant` | Added the same helper call; router guard → `require_tenant_mutation_permission` |
| 4 | `payment.router::create_order` `POST /v1/payments/orders` | `create_payment_order` skipped `_require_trusted_tenant` while sibling `request_payout` (a more sensitive financial op, same file) already enforces it. Confirmed `customer` role does not hold `TENANT_BILLING_MANAGE` — this is a tenant/admin-side gap, not a customer payment-flow regression | Added `_require_trusted_tenant(tenant_id)`; router guard → `require_tenant_mutation_permission` |
| 5 | `payment.router::generate_invoice` `POST /v1/payments/tenants/{tenant_id}/invoice` | Same gap as `create_order`, same file | Same fix |
| 6 | `rag.router::create_kb` `POST /v1/rag/knowledge-bases` | Zero tenant scoping on a client-supplied `tenant_id` | Added an explicit check against `_require_trusted_tenant()`'s return; router guard → `require_tenant_mutation_permission` |
| 7 | `rag.router::update_kb` `PATCH /v1/rag/knowledge-bases/{kb_id}` | Used the **untrusted** `_get_kb` lookup instead of sibling `delete_kb`'s `_get_kb_trusted` — any tenant-side actor could mutate any other tenant's KB by guessing its UUID | Swapped to `_get_kb_trusted`; router guard → `require_tenant_mutation_permission` |
| 8 | `dispatch.router::accept_job` `POST /v1/dispatch/jobs/{job_id}/accept` (+ sibling `reject_job`, found during tracing, not on the original 21) | Neither verified `staff_id` matched the caller's own identity — any authenticated user could accept/reject a job as an arbitrary staff member | Added `staff_id != self.actor_id` rejection (super_admin exempt), mirroring the `create_session` identity-spoofing fix from Slice 2F-39A2R |
| 9 | `data_science.router::acknowledge_anomaly` `POST /v1/ds/anomalies/{id}/acknowledge` | Zero tenant scoping while every other mutation in `DSService` already uses `_require_trusted_tenant` | Added the post-fetch ownership check (non-oracular `NotFoundException`); router guard → `require_tenant_mutation_permission` |

## 4 routes verified SAFE (no fix needed)

| Route | Why safe |
|---|---|
| `media.router::delete_file` | Already fixed in the Slice 2F-31A residual work — service calls `_require_trusted_tenant` before the query. Outwardly bare router guard, but a compensating service-layer check exists — matches the `rotate_api_key` precedent from 2F-39A2R |
| `ai_chat.router::ai_chat` | Auth is enforced transitively via `_svc`'s own `Depends(get_current_user)` (missed by the bulk-grep classifier since it isn't on the endpoint's own signature). Operates only on the caller's own message/history, no cross-tenant/cross-user data involved |
| `document.router::record_signature` | Authenticated by a Redis-backed, single-use, expiring signing token (not a user session) — a legitimate signed-callback pattern, matching the permitted "signed callback/webhook" disposition |
| `rag.router::search` | Read-only vector search (own docstring: "no LLM generation, returns ranked chunks"); no persistent mutation |

## 3 routes untouched — N01 standing blocker (not reopened)

`media.router::initiate_upload`, `media.router::confirm_upload`,
`media.new_router::delete_media` remain `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`,
per the mission's explicit instruction never to reopen N01 in these slices.

## 5 routes remain genuinely `PRODUCT_DECISION_REQUIRED`

See `known-limitations.md` for the full evidence record on each (fully
qualified identity, mutation behavior, auth/permission/scope, tenant
derivation, client-controlled identifiers, service method, known callers,
exact missing decision, risk, candidate dispositions).

| Route | Why not force-fixed |
|---|---|
| `analytics.router::ingest_event` | No established sibling tenant-scoping pattern in this file (the read-side `event_stream` also accepts an unvalidated optional `tenant_id`); no in-process caller found to clarify whether this is meant to accept cross-tenant/system-sourced events or self-reported ones only |
| `appointment.router::hold_slot` | No established self-check sibling in this file; staff-assisted booking (staff holding a slot on behalf of a customer) is a plausible legitimate use of a non-matching `customer_id`, so forcing "customer_id must equal caller" could break a real flow — genuine caller-model ambiguity |
| `platform_commerce.billing_endpoint::route_operation` | **HIGH risk** — actually dispatches real financial operations (commission/subscription engines) yet is far less restricted than its sibling config routes (`require_super_admin`). Whether legitimate callers are tenant owners self-triggering their own billing operations, or this should be platform-internal-only, cannot be determined from code alone |
| `notification.router::send_notification` | No established sibling pattern for a "send"-shaped mutation (unlike the CRUD-shaped tenant-settings routes); genuine ambiguity over whether this is meant to be callable by any authenticated user or restricted to platform-internal triggers |
| `notification.router::retry` | Same ambiguity as `send_notification`, same file |

## Denominator effect

`PRODUCT_DECISION_REQUIRED` count: **21 → 5** (this slice), plus the 3
standing N01 rows (unchanged, separate blocker, not counted toward this
reduction). Confirmed authorization defects found and fixed this slice: **9**
(across 7 distinct route pairs/singles, plus 1 bonus sibling fix).
