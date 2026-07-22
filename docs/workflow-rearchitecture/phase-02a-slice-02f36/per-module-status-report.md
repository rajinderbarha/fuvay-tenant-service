# Per-Module Status Report

| Module | Set A | Set B included | Final protected | Denom. contribution | Held resolved | Status | Blocker |
|---|---|---|---|---|---|---|---|
| enterprise_grid_saved_views | 4 | 0 | 4 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| enterprise_grid_preferences_exports | 2 | 0 | 2 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| admin_catalog_provider_setup | 4 | 0 | 4 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| profile_technician_self_service | 3 | 0 | 3 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| profile_universal_self_service | 1 | 0 | 1 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none (product decision on whether self-service should EVER be role-restricted remains open, tracked in product-decisions-required.md, but does not block this route's access-scope closure) |
| marketing_automation_provider | 3 | 0 | 3 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| analytics_provider_reports | 1 | 0 | 1 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| serviceability | 0 | 0 (1 read-only excluded) | 0 | 0 | 1 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none (READ_ONLY_EXCLUDE, not a mutation) |
| chat | 0 | 1 | 1 | +1 | 1 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| inventory | 0 | 5 | 5 | +5 | 5 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| bookings | 0 | 0 (1 already-protected exclude) | 0 (already counted elsewhere) | 0 | 1 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none (CUSTOMER_SELF_SERVICE_EXCLUDE, already protected pre-slice) |
| appointments | 0 | 7 | 7 | +7 | 7 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| catalog | 0 | 2 | 2 | +2 | 2 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| dispatch | 0 | 2 | 2 | +2 | 2 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| ds | 0 | 4 (2 read-only excluded) | 4 | +4 | 6 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| settings | 0 | 2 | 2 | +2 | 2 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| notifications | 0 | 1 | 1 | +1 | 1 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |

**All 17 modules (7 Set A + 10 held-registry) independently reached
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`.** No module was blocked
this slice. Totals: 18 Set A routes closed (c=18), 24 Set B routes
canonically added and protected (a=h=24), all 28 Set B routes received a
final disposition (r=28).
