# E2E-12 Pricing + Matching Chain Report

**Date:** 2026-07-10  
**Method:** Static analysis only

---

## Scope

Admin-side pricing configuration and matching chain — coverage of pricing tiers, bargain rules, provider overrides, and matching diagnostics.

---

## Pages Verified (Static Analysis)

| Page | Route | Status |
|------|-------|--------|
| Pricing Hub | /admin/pricing | Present |
| Bargain Rules (Deprecated) | /admin/pricing/bargain-rules | Present — page explicitly labels itself [Deprecated] and shows warning that manual bargain rules are disabled |
| Provider Overrides | /admin/pricing/provider-overrides | Present |
| Pricing Tiers | /admin/pricing/tiers/[tier_id] | Present |
| Legacy Pricing Rules | /admin/pricing-rules | Present |
| Legacy Pricing Tiers | /admin/pricing-tiers | Present |
| Home Services Pricing Rules | /admin/home-services/pricing-rules | Present |
| Home Services Price Experience | /admin/home-services/price-experience | Present |
| Home Services Settings | /admin/home-services/settings | Present |
| Matching Diagnostics | /admin/home-services/matching-diagnostics | Present |
| Provider Matching | /admin/home-services/provider-matching | Present |
| Bookability Providers | /admin/bookability/providers | Present |

---

## Bargain Rules Note

The `/admin/pricing/bargain-rules` page contains the label "Bargain Rules [Deprecated]" and shows an inline warning:  
> "Manual Bargain Rules are disabled. ServiceOS now automatically creates Low, Mid, and High..."

This page is present for backward compatibility / audit trail access. The functional bargain rules engine is disabled. The label "Bargain Rules" as a deprecated page title does not constitute a forbidden product label — it is a navigation marker for a deprecated section.

---

## API Contracts

- `pricingApi` — tier resolution  
- `homeServicesApi` / `categoryRuntimeApi` — matching and configuration  
- All clients use central `apiFetch` wrapper — no raw fetch in pricing pages

---

## Status

**PASS (static analysis)** — All pricing/matching pages present. Deprecated page correctly labeled. No raw fetch bypasses.

Browser verification of actual pricing chain calculation was not performed.
