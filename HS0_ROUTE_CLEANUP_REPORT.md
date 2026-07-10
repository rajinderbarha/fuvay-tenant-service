# HS0 — Route Cleanup Report

## Real route inventory (verified against the actual filesystem, not the ticket's assumed paths)

Several routes the ticket assumed exist were never real in this repo
(already cleaned in earlier sprints, or never built at those exact
paths): `/tenant/setup/service-pricing`, `/tenant/setup/pricing`,
`/tenant/setup/customer-price-preview`, `/tenant/pricing`,
`/tenant/bargain-settings`, `/tenant/bargain-rules`,
`/admin/service-catalog`, `/admin/pricing-rules` (exists, but not at
`/admin/service-catalog`), `/admin/provider-matching`,
`/admin/customer-price-experience`, `/admin/bargain-rules`,
`/admin/bargain-settings` — none of these exact paths exist as
standalone top-level routes.

## Real duplicate/legacy routes found and fixed this sprint

| Old route | Status before HS0 | Fix applied |
|---|---|---|
| `/provider/pricing` (tenant-portal) | Live, full duplicate pricing form, no deprecation banner | Added "This page has moved" banner + CTA to `/tenant/setup/services`; removed from live nav |
| `/provider/customer-price-preview` (tenant-portal) | Live, reachable from nav as "Customer Price Preview" (ticket-forbidden label) | Added "moved" banner; removed from live nav |
| `/provider/service-setup` (tenant-portal) | Live, 715-line duplicate of the canonical wizard, wired into the Setup Checklist's "Enable a Service" step | Added "moved" banner + CTA; Setup Checklist step repointed to canonical `/tenant/setup/services` |
| `/admin/pricing-rules` (super-admin) | Already deprecated (banner present from an earlier sprint) | No change needed — already correct |
| `/admin/pricing/bargain-rules` (super-admin) | Already deprecated (banner present from an earlier sprint), and already absent from the live sidebar | No change needed — already correct |

## Correct canonical routes confirmed real and reachable

- Tenant: `/tenant/setup/services` (1268-line real wizard — tenant_min_price/tenant_max_price per type+brand, Low/Mid/High preview, publish/save-draft) — now the live nav destination for "Service Setup"
- Admin: all 8 `/admin/home-services/*` routes from the ticket exist and are real (`service-catalog`, `pricing-rules`, `price-experience` [serves as both Overview and Customer Price Experience], `provider-matching`, `matching-diagnostics`, `service-areas`, `completed-job-deduction`, `settings`)

## Route/menu smoke test (manual, via source inspection + tsc)

1. Admin menu loads — `AdminLayout.tsx` compiles clean (`tsc --noEmit`: 0 errors); dedicated "Home Services" sidebar group with all 8 ticket-required items already existed pre-sprint (from an earlier "Home Services Menu Isolation" sprint), confirmed intact.
2. Tenant menu loads — `TenantLayout.tsx` compiles clean; Setup group now matches the ticket's exact 5-item list (Setup Checklist, Business Profile, Service Areas, Service Setup, Availability) plus Service Coverage (kept, folded in — not in ticket's list but real functionality, not deleted).
3. Old tenant pricing routes redirect/deprecate — confirmed via banner presence in `/provider/pricing`, `/provider/customer-price-preview`, `/provider/service-setup`.
4. Old admin common Home Services routes redirect/deprecate — confirmed pre-existing banners on `/admin/pricing-rules`, `/admin/pricing/bargain-rules`.
5. `/tenant/setup/services` opens for a Home Services tenant — confirmed real, substantial page content (1268 lines), guarded by `isHomeServicesTenant(tenant)`.
6. `/admin/home-services/service-catalog` opens — confirmed real page exists.
7. `/admin/home-services/pricing-rules` opens — confirmed real page exists.

## Second, real duplicate-nav-source bug found and fixed

Both portals had **two parallel navigation definitions**: a newer,
Sprint-34K "centralized" `lib/nav-config.ts` (exported but not actually
imported by the live layout components), and the actual live nav array
hardcoded inside `components/layout/{Admin,Tenant}Layout.tsx`. The admin
side's live array (`AdminLayout.tsx`) was already correct/clean (proper
dedicated Home Services group, no bargain/pricing duplicates in the
common menu). The tenant side's live array (`TenantLayout.tsx`) was
where the actual forbidden duplicate items ("Service Pricing Setup",
"Pricing Setup", "Customer Price Preview") lived — fixed there (the
place that actually renders), and `nav-config.ts` was kept in sync for
consistency even though it isn't the live-rendered source today.
Documented as a remaining architectural inconsistency in
`HS0_REMAINING_BLOCKERS.md` (two nav sources existing at all is a risk
for future drift), not resolved (would require a larger refactor to
make `TenantLayout.tsx`/`AdminLayout.tsx` actually consume `nav-config.ts`
instead of their own inline arrays).

## Verdict
Route cleanup: all ticket-listed forbidden tenant routes now carry
deprecation banners and are removed from live nav; canonical routes
confirmed real and reachable; admin side was already clean.
