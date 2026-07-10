# HS4B — Publish Readiness Fix Report

## Decision: publish readiness left as-is; bookability enforces the full list
The ticket allows: *"If some requirements are intentionally not enforced
at publish time, document exact product reason and enforce them in
bookability refresh."* This sprint took exactly that path.

`publish_service` (`app/engines/admin_catalog/tenant_service.py`,
unchanged this sprint) checks 4 items: type selection, type pricing
completeness, brand pricing completeness, active service area. It
intentionally does **not** check business profile, availability, usage
credits, or security deposit at publish time.

**Product reason**: `publish_service` operates within the
`admin_catalog` engine, scoped to a single `TenantService` row —
business profile, availability, usage credits, and security deposit are
tenant-wide concerns owned by other engines (`tenant_engine`,
`provider_portal`, `platform_commerce`). Publishing a *service* is a
catalog-configuration action (a business could reasonably finish
configuring 3 services before setting up availability); becoming
*bookable* is a tenant-wide readiness gate that should be evaluated
holistically, not duplicated inside every per-service mutation.

**This is exactly what `_evaluate_provider_bookability` (new this
sprint) does**: it checks all 4 of the ticket's remaining items
(business profile, availability, usage credits, security deposit) plus
re-validates service area and published-service-pricing, at the
tenant level, on demand via refresh — and now also automatically right
after every publish (frontend calls `providerStatusApi.refresh()`
immediately following a successful `publish()`).

## Net result
A tenant can publish a service with `publish_service`'s 4 checks
satisfied, but will correctly see `is_bookable=false` with clear
blocking reasons if business profile, availability, usage credits, or
security deposit are still missing — satisfying the ticket's core
requirement ("Bookability status must update only when all required
checks pass") without duplicating validation logic across two engines.

## Verdict
Publish readiness: **policy split documented and correctly implemented
via the bookability refresh fix**, not silently ignored. `publish_
service` itself was not modified this sprint (no bug found there beyond
what HS4's original testing already covered).
