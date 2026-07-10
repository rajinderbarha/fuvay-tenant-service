# FINAL-L5-02 — Deprecated & Legacy API Register

| Path / router | Reason retained | Canonical replacement | Current consumers | Removal condition | Target |
|---|---|---|---|---|---|
| `/v1/admin/service-setup/templates*` (Sprint 34F router `admin_catalog.service_setup_template_router`) | Still mounted; possible active frontend consumer | `/v1/admin/service-setup-templates*` (P0-Enterprise `service_setup.templates_router`, migration-097 schema) | Unknown — needs consumer audit | After confirming no frontend calls the `/service-setup/templates` prefix | FINAL-L5-03 |
| `app/engines/brands/admin_router.py`, `provider_router.py` | Already unmounted (dead) | `admin_catalog/brand_router.py`, `brand_provider_router.py` | None (unmounted) | Delete files after final confirmation | FINAL-L5-03 |
| `tenant_wallets` + `ProviderCreditWalletService` (Sprint 23) | Legacy compatibility wrapper; reporting reads | `tenant_billing.credit_balance` + `usage_credit_ledger` | Dashboard/marketing/analytics reporting only (not bookability) | After reporting migrated off wallet reads | FINAL-L5-03+ |
| `jobs` (field_ops) + `/v1/jobs/*`, `/v1/staff/me/jobs/*`, `/v1/customer/jobs/*` | Legacy Field Ops job system | `service_jobs` + `/v1/admin/final-records/jobs*`, `/v1/staff/service-jobs*`, `/v1/customer/my-activity/jobs*` | May serve non-home-services verticals | After consumer audit confirms home-services fully migrated | FINAL-L5-03+ |
| 4 disabled plugin routers (`leads`, `loyalty`, `real_estate`, `promo`) | Intentionally disabled (only home_services vertical active) | N/A (feature-flagged off) | None | When/if those verticals activate | vertical activation |

## Machine-readable
`deprecated-api-register.json`.

## Note
No legacy endpoint was **removed** this sprint — each needs a consumer audit first, per the "don't delete unproven-safe" discipline carried from FINAL-L5-00. This register makes the future removal work tractable.
