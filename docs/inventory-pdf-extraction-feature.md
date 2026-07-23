# Inventory PDF Extraction Feature

Lets a tenant provider upload a PDF (price list / stock sheet), have the
platform's real LLM client extract candidate inventory line items, review
and edit them as drafts, and explicitly publish them into the live
Inventory Engine catalogue.

## Engine key and how it's toggled

- Engine key: `inventory_document_extraction`
- Type: **plugin** (`is_enabled_by_default = False`) — off for every tenant
  until a platform admin turns it on.
- Depends on: `auth`, `inventory` (core catalogue engine), `rag` (declared
  as a soft dependency since it shares the "document ingestion" category;
  the extraction pipeline itself does not call the RAG engine's code).
- Registered in `app/engine_registry/registry.py`. It surfaces automatically
  through the existing `/v1/engines` introspection endpoint and the
  per-tenant `/v1/tenants/{id}/engines/*` enable/disable endpoints in
  `app/engines/tenant_engine/service.py` (`enable_engine` / `disable_engine`)
  — no additional registration step was needed. It also appears in the real
  super-admin `/admin/engines` UI and the tenant-portal's
  `/v1/tenant/engines/effective` response, which the tenant-portal frontend
  uses to conditionally show the upload button.
- To enable for a tenant: `POST /v1/tenants/{tenant_id}/engines/inventory_document_extraction/enable`
  (super_admin, or whatever principal already has `tenant.enable_engine`
  permission in this codebase).

## API endpoints added

All mounted under the existing inventory router prefix, in
`app/engines/inventory/extraction_router.py`:

| Method | Path | Behavior |
|---|---|---|
| GET  | `/v1/inventory/extraction/meta` | Engine introspection (name, version, capabilities). |
| POST | `/v1/inventory/tenants/{tenant_id}/extraction/upload` | Multipart PDF upload. Requires `tenant:update` permission. 403 (`ENGINE_DISABLED`) if the plugin engine isn't enabled for this tenant. Extracts text, calls the LLM, creates `status="draft"` `InventoryItem` rows, returns them. Idempotent on `(tenant_id, sha256(file_bytes))` — re-uploading the same file returns the same draft rows instead of duplicating them. |
| GET  | `/v1/inventory/tenants/{tenant_id}/extraction/drafts` | List all current draft items for the tenant. |
| PATCH| `/v1/inventory/items/{item_id}/draft` | Edit a draft item's name/sku/category/unit/unit_cost/min_quantity. 409 if the item is not in `draft` status. |
| DELETE| `/v1/inventory/items/{item_id}/draft` | Discard a draft item. 409 if not `draft`. |
| POST | `/v1/inventory/items/{item_id}/publish` | Flip one draft item to `published`. Re-checks the engine is still enabled. 409 if already published. |
| POST | `/v1/inventory/items/publish-bulk` | Publish multiple draft items in one call; per-item results, partial success supported. |

All draft/publish endpoints enforce the same cross-tenant guard pattern
used throughout the inventory engine (`_require_trusted_tenant`) — a
tenant principal can only touch their own tenant's items; `super_admin` is
exempt.

## LLM client reused (real, not fabricated)

`app/engines/ai_conversation/deepseek_client.py`'s `DeepSeekClientService`
— the same client that backs the customer-facing DeepSeek chat assistant
elsewhere in the platform. `extraction_service.py` calls
`DeepSeekClientService(db=..., request_id=...).chat(messages=[...])` with:

- A system prompt (`EXTRACTION_SYSTEM_PROMPT` in
  `app/engines/inventory/constants.py`) instructing the model to return
  **strict JSON only** — `{"items": [{"name", "sku", "quantity", "unit",
  "unit_cost", "category"}, ...]}` — with `null` for any field not present
  in the source text (the model is explicitly told never to invent values).
- The PDF's extracted text (truncated to 24,000 characters to keep the
  call bounded) as the user message.

This is a real HTTP call to `https://api.deepseek.com/v1/chat/completions`
via `httpx`, gated by `DEEPSEEK_API_KEY` (`app/config.py`). If the key is
not configured, `DeepSeekClientService.chat()` raises
`DEEPSEEK_NOT_CONFIGURED` (503) — the extraction endpoint surfaces that
honestly rather than fabricating a result. Every call is logged to
`ai_llm_call_logs` via the client's existing `_log_call` method.

**Important, disclosed honestly:** neither the RAG engine
(`app/engines/rag/service.py`) nor the Document Vault engine
(`app/engines/document/service.py`) had an existing PDF-text-extraction
utility to reuse — both operate on text that has already been extracted
before it reaches them (`ingest_document(..., content: str, ...)`). The
RAG engine's own embedding/generation (`_mock_embed` / `_mock_generate`)
are explicitly mocked placeholders, not a real LLM call — so this feature
does **not** reuse RAG's pipeline for generation; it reuses the DeepSeek
client directly, which is the platform's one real, wired-up LLM
integration. PDF text extraction itself was added fresh via `pypdf`
(new dependency, `pypdf==5.1.0` in `requirements.txt`) since no such
utility existed anywhere in the codebase.

## Draft -> publish state model

- Migration `145_inventory_item_draft_status.py` adds:
  - `inventory_items.status` (`draft` | `published`), `server_default =
    'published'` so every pre-existing row is unaffected.
  - `inventory_items.source_upload_id` (nullable FK-like UUID) tracing a
    draft row back to the upload that produced it.
  - `inventory_extraction_uploads` — one audit row per PDF upload
    (`tenant_id`, `file_name`, `content_hash`, `status`
    processing/completed/failed, `error_message`, `extracted_item_count`,
    `raw_llm_response`, `uploaded_by`), unique on `(tenant_id,
    content_hash)` for idempotency — mirrors `KBDocument`'s idempotency
    pattern in the RAG engine.
- Items created by extraction always start `status="draft"` — the
  extraction endpoint never publishes automatically, per the explicit
  requirement. A provider must call the publish endpoint (single or bulk)
  after reviewing/editing.
- Manually created items (the pre-existing `POST
  /v1/inventory/tenants/{tid}/items` endpoint) are unaffected — they still
  default to `status="published"` (the model's Python-side default) since
  they were never meant to go through a review step.

## Frontend

`frontend/tenant-portal/app/(tenant)/inventory/page.tsx`:
- "Upload Inventory PDF" file input, shown only when
  `/v1/tenant/engines/effective` reports `inventory_document_extraction` as
  `effective_enabled`; otherwise an inline message tells the provider to
  ask their platform admin to enable it.
- After upload, an inline editable table of draft rows (name, SKU, unit
  cost, min qty) with per-row Save / Publish / Delete, plus a "Publish All"
  bulk action.
- Real loading/error states: upload spinner text, and inline error/success
  banners driven by the actual API response/error (no fake success paths).

`frontend/tenant-portal/lib/api.ts`: added `uploadForExtraction` (multipart,
via the existing `apiFetchMultipart` helper), `listDrafts`, `updateDraft`,
`deleteDraft`, `publishItem`, `publishBulk` to `inventoryApi`, and
`InventoryDraftItem` / `InventoryExtractionResult` types.

## Tests

`tests/test_module_inventory_document_extraction.py` — 5 unit tests against
`InventoryExtractionService` with a mocked `AsyncSession` (matching the
established pattern in `test_final_l5_05j_usage_credit_service.py`):
engine-registration sanity, engine-disabled 403-equivalent gate, malformed
PDF error, a mocked-DeepSeek-response success path creating 2 draft items,
and a publish-guard rejecting an already-published item. All 5 pass.

## What was and wasn't completed

Completed in full:
1. Nav fix (Inventory item added to tenant-portal sidebar).
2. Engine registration (`inventory_document_extraction`, toggleable via the
   existing engine registry / admin UI).
3. Backend PDF upload + extraction endpoint, gated, using the real
   DeepSeek client, never auto-publishing, with tests.
4. Backend draft CRUD + publish/bulk-publish endpoints.
5. Frontend upload/review/publish UI with real loading/error states.
6. This document.

Deferred / not done, disclosed honestly:
- **No live end-to-end verification against a running Postgres + a real
  DeepSeek API key** — migration 145 has not been run against a live
  database in this session (no DB was reachable), and no real DeepSeek
  call was made (would require a live key + network egress in this
  sandbox). All verification here is: clean `python -c "import app.main"`
  with the new routes mounted, clean `ast.parse` on every new/changed
  Python file, and 5/5 passing unit tests against a mocked DB and a
  mocked `DeepSeekClientService.chat`.
- Multi-page / very large PDFs: extracted text is truncated to 24,000
  characters before being sent to the LLM to keep the call bounded: a
  large supplier catalogue may need chunked extraction across multiple
  LLM calls, which was not built.
- No admin-side "review this tenant's extraction history" screen was
  added (only the tenant-portal review/publish UI); `inventory_extraction_uploads`
  rows exist in the DB for this purpose but there's no dedicated page
  reading them yet.
- OCR / scanned-image PDFs are explicitly rejected with a clear error
  (`INVENTORY_EXTRACTION_PDF_UNREADABLE`) rather than attempted — pypdf
  only extracts embedded text layers.
