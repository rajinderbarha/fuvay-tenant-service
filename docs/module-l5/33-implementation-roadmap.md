# MODULE-L5-00 — Dependency Graph, Implementation Order and Sprint Roadmap

## Dependency graph (module-domain level)

Repository evidence (migration ordering, engine `dependencies` lists visible in `app/main.py`/router mounting, and the FINAL-L5-05 chain's own discovered dependency order) supports the mission brief's own suggested order without material change:

```
Identity & Access (auth, roles_permissions, security)
  -> Tenant Onboarding (tenant_engine, public_registration)
    -> Geography/Serviceability (geo, location_engine, serviceability)
      -> Catalog (service_catalog, admin_catalog, vertical_catalog, brands, service_setup)
        -> Pricing (pricing)
          -> Providers/Staff (provider_portal, field_ops, dispatch)
            -> Packages/Credits/Deposits (package_commerce, usage_credits, customer_credits, entitlement, platform_commerce billing)
              -> Booking/Matching (booking, home_service_booking, appointment, coaching_appointment)
                -> Job Lifecycle (execution, quote_checklist, final_records, home_service_assignment)
                  -> Finance/Commission (finance_hub, invoice_payment, vertical_billing[dead]->platform_commerce)
                    -> Notifications/Audit/Workers (notification, platform_notifications, workflows)
                      -> Reviews/Rewards (review, customer_reviews, loyalty, trust_quality)
                        -> Compliance/Security Ops (compliance, security)
                          -> Media/Storage/Exports (media, document, enterprise_grid)
                            -> System Config (settings_engine, engine_mgmt, dashboard_command_center)
                              -> Marketing (marketing, marketing_automation, marketing_command_center, leads, real_estate_lead)
```

Cross-cutting (depended on by nearly everything, not sequenced): `analytics`, `data_science`, `webhook`, `chat`/`ai_chat`/`ai_conversation`, `rag`.

## Recommended implementation order (adopted from mission brief, unchanged — repository evidence supports it)

1. Identity and Access — **must include all 10 roles**, not just the 5 `admin_*` roles (per MODULE-L5-00-001)
2. Tenant Onboarding and Verification
3. Geography, Tier, Zone and Serviceability
4. Catalog, Types, Brands and Offerings
5. Pricing and Bargain
6. Provider, Staff and Availability — **must include `staff_app_mobile`** (per MODULE-L5-00-004), not Super Admin/Tenant views of staff alone
7. Packages, Credits and Security Deposit
8. Booking, Matching and Scheduling — **must re-verify the cancellation/reschedule pipeline connection** (MODULE-L5-00-005) before being marked complete
9. Job Lifecycle, Quotes, Parts and Completion
10. Finance, Ledger, Invoice and Commission — **must resolve the `vertical_billing`/`platform_commerce` duplication** (MODULE-L5-00-002) before certifying
11. Notifications, Audit, Workers and Cron
12. Reviews, Rewards, Badges and Health
13. Compliance and Security Operations — **must resolve Security Policy ownership** (MODULE-L5-00-006) before certifying
14. Media, Storage and Exports
15. System Configuration and Platform Health
16. Marketing
17. Super Admin application completion (closest to done — 13 prior sprints of real work)
18. Tenant application completion (real prior work exists in `PHASE_6B_TENANT_*`, never reconciled — start there, don't restart from zero)
19. Staff application completion (least prior work — see MODULE-L5-00-004)
20. Customer application completion (mobile app under active separate `CUSTOMER-L5-*` certification — coordinate, don't duplicate; web app is minimal, 8 routes)
21. Cross-application integration
22. Final platform Level 5 gate

## Future sprint plan (bounded set — the full 68-module x 5-phase matrix is not generated in this sprint; this is the authoritative starting sequence)

| Sprint ID | Scope | Depends on | READY target |
|---|---|---|---|
| `MODULE-L5-00A` | Reconcile pre-05 `final-l5-00..04b` granular docs and pre-05 "release candidate" artifacts against current code; resolve `vertical_billing` disposition | MODULE-L5-00 (this sprint) | `READY_MODULE_L5_00A_RECONCILIATION_CERTIFIED` |
| `MODULE-L5-01` | Identity & Access — full 10-role requirement/permission/session matrix | MODULE-L5-00 | `READY_MODULE_L5_01_IDENTITY_L5_CERTIFIED` |
| `MODULE-L5-02` | Tenant Onboarding & Verification | MODULE-L5-01 | per module |
| `MODULE-L5-03` | Geography/Serviceability | MODULE-L5-02 | per module |
| `MODULE-L5-04` | Catalog/Pricing | MODULE-L5-03 | per module |
| `MODULE-L5-05` | Providers/Staff (incl. `staff_app_mobile` first real certification) | MODULE-L5-04 | per module |
| `MODULE-L5-06` | Packages/Credits/Deposits (resolve billing duplication) | MODULE-L5-05 | per module |
| `MODULE-L5-07` | Booking/Matching (re-verify cancellation/reschedule connection) | MODULE-L5-06 | per module |
| `MODULE-L5-08` | Job Lifecycle | MODULE-L5-07 | per module |
| `MODULE-L5-09` | Finance/Commission | MODULE-L5-08 | per module |
| `MODULE-L5-10` | Notifications/Audit/Workers | MODULE-L5-09 | per module |
| `MODULE-L5-11..16` | Reviews/Compliance/Media/Config/Marketing | as above | per module |
| `MODULE-L5-17..20` | Per-application completion (Super Admin, Tenant, Staff, Customer) | all above | per application |
| `MODULE-L5-21` | Cross-application integration | all above | integration gate |
| `MODULE-L5-22` | Final platform Level 5 gate | all above | `READY_PLATFORM_ALL_MODULES_FUNCTIONALLY_COMPLETE_LEVEL_5_CERTIFIED` |

Each future sprint should follow the mission brief's own `MODULE-[ID]-L1..L5` phase structure (Requirements/Gap Audit -> Database/Backend -> Frontend -> Integration -> E2E Certification), combining phases only where a module is small enough to justify it (e.g. `vertical_billing`'s cleanup is L1+L2 only).
