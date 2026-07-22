# Known Limitations — Slice 2F-39A3

## 21 routes flagged `PRODUCT_DECISION_REQUIRED` — a real, disclosed, unverified risk

These are **not confirmed safe** and **not confirmed defective** — each
needs the same service-layer tracing rigor already applied to the
confirmed defects before either claim can be made.

### High-priority: bare `require_permission` where a sibling uses `require_tenant_mutation_permission` (matches a confirmed real-defect pattern twice already)

| Route | Module |
|---|---|
| `POST /v1/catalog/items/{item_id}/deactivate` (`deactivate_item`) | service_catalog.router |
| `POST /v1/inventory/tenants/{tenant_id}/replenish` (`replenish`) | inventory.router |
| `DELETE /v1/media/{file_id}` (`delete_file`) | media.router |
| `POST /v1/notifications/tenants/{tenant_id}/channels/{channel}/test` (`test_channel`) | notification.router |
| `POST /v1/payments/tenants/{tenant_id}/invoice` (`generate_invoice`) | payment.router |
| `POST /v1/payments/orders` (`create_order`) | payment.router — **already independently documented** in the Slice 2F-26H observation corpus: "tenant_id, customer_id, amount all from body" |
| `POST /v1/rag/knowledge-bases` (`create_kb`) | rag.router |
| `PATCH /v1/rag/knowledge-bases/{kb_id}` (`update_kb`) | rag.router |

### Bare `get_current_user`, not individually traced to a service-layer ownership check this slice

`ai_chat.router::ai_chat`, `analytics.router::ingest_event`,
`appointment.router::hold_slot`, `platform_commerce.billing_endpoint::route_operation`,
`dispatch.router::accept_job`, `document.router::record_signature`,
`data_science.router::acknowledge_anomaly`, `notification.router::send_notification`,
`notification.router::retry`, `rag.router::search`,
`chat.router::create_conversation` (partially traced — participant
handling not deeply re-verified).

### N01 territory (not reopened, standing status preserved)

`media.router::initiate_upload`/`confirm_upload`,
`media.new_router::delete_media` — remains
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`.

## Read-path privacy gaps

Tracked separately in `read-path-privacy-ledger.md`, per explicit
instruction — never folded into the mutation-defect or route-census
arithmetic.

## Other

- No dedicated `verify_2f39a3.py` was built.
- Full backend regression run once, not twice, given its ~15-25 minute cost.
- The 149-route classification, while complete in count, relied on
  bulk-scanned guard-pattern extraction (a scripted grep across all 28
  modules) rather than the fully manual, line-by-line source reading
  applied to the 2 confirmed-and-fixed defects. This is a faster but
  less exhaustive method than prior tranches used for smaller batches —
  disclosed here rather than presented as equally rigorous.
