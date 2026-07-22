# Updated Risk Scoring Model (WS5)

## Methodology

Every score in
[remaining-module-risk-scores.csv](remaining-module-risk-scores.csv) is
derived from direct service-layer inspection performed this slice (not
inherited from 2F-32's `UNKNOWN` placeholders) — see
[complete-service-inspection.csv](complete-service-inspection.csv) for
the raw evidence. No stale risk score was retained without a fresh
inspection this slice.

## Headline finding: `rag_query`

`RAGService` never receives `actor_tenant_id` at all, and `_get_kb(kb_id)`
queries `WHERE id == kb_id AND is_active == True` with **zero tenant
predicate**. Any authenticated user of any tenant can query — and
potentially exfiltrate content from — another tenant's knowledge base by
supplying its `kb_id`. This is a genuine cross-tenant data-exposure
finding, not merely an access-scope gap, discovered by this slice's
service-level inspection (2F-32 had this route in a different, lower-risk
context and did not inspect the service). This finding moves `rag_query`
into Slice 2F-35 alongside `webhook_endpoint_management`.

## Second finding: most "UNKNOWN" modules turned out low-risk

Direct inspection of `admin_catalog_provider_setup`, `profile_technician_
self_service`, `profile_universal_self_service`, `marketing_automation_
provider`, and `analytics_provider_reports` found that every one of them
already derives tenant server-side (`self.tenant_id`, `_tid(u)`, or is
inherently self-service with no ID parameter at all) — the sole remaining
gap in each is the missing access-scope-aware guard, not a cross-tenant
authorization hole. This is why they are assigned to the lower-urgency
2F-36 batch rather than 2F-35.

## Third finding: `enterprise_grid_preferences_exports`

`ColumnPreferenceService.save_preferences` is keyed by `user_id`
(self-service, no cross-tenant risk). `ExportService.create_export_job`
already has partial per-resource export-permission gating (confirmed by
an inline code comment referencing a prior incident, `FINAL-L5-05O/05R`)
— the route-level gap is real but narrower than a naive "bulk data
export = high risk" assumption would suggest.
