# Alternate Route and Bypass Report

## Method
The runtime mutation-route inventory (`inventory_mutation_routes.py`) surfaced 24 distinct router modules serving the 185 tenant-facing mutation endpoints — 8 more than Slice 2E's original 16-file survey anticipated (`execution.home_service_router`, `execution.coaching_router`, `execution.real_estate_router`, `field_ops.checklist_router`, `field_ops.staff_router`, `home_service_assignment.staff_router`, `media.new_router`, `profile.router`, `tenant_engine.portal_router` — several of these were not part of the original `tenant_router.py`/`provider_router.py` naming-pattern search). This alone is a materially useful finding: **a filename-pattern-based search for "tenant mutation routers" would have missed ~40% of the real router modules involved.**

## Confirmed capability-duplication risks (found, not yet resolved)

| Capability | Canonical-looking route | Alternate route found | Guard comparison |
|---|---|---|---|
| Job execution actions | `app/engines/execution/home_service_router.py` (`/v1/staff/service-jobs/*`, `/v1/provider/service-jobs/*`) | `app/engines/home_service_assignment/staff_router.py` and `provider_router.py` (also `/v1/staff/service-jobs`, `/v1/provider/service-jobs` prefixes — confirmed overlapping paths from Slice 1's audit, e.g. both define `POST .../accept`) | Both show `UNVERIFIED` guard status in this slice's data — **cannot yet confirm one is stronger than the other**, since neither shows a detected role/permission dependency at the route level |
| Staff job actions (legacy) | (canonical `service-jobs` above) | `app/engines/field_ops/staff_router.py` (6 endpoints, `UNVERIFIED`) | Same guard-status finding — this is the legacy field_ops path Phase 1 already flagged as parallel/legacy; still mounted, still has mutation endpoints, still shows no detected route-level guard |
| Checklist templates | `field_ops/checklist_router.py` (6 endpoints, `PERMISSION_ONLY_NOT_ACCESS_SCOPE_AWARE`) | No alternate found this pass | N/A |

## What was NOT resolved
Whether the `UNVERIFIED` (no detected route-dependency) endpoints have an equivalent check inside the handler body or service method was not individually traced for all 83 such endpoints — this requires reading each handler, which was not completed this slice (see `service-layer-bypass-report.md` and `known-limitations.md`). **No tenant read-only user may mutate through a weaker alternate path** remains unproven for the job-execution/field_ops overlap specifically, pending that trace.

## No new bypass was created this slice
This slice added no new endpoint and modified no router — the one code change (`update_permissions`'s session revocation) does not introduce or remove any route.
