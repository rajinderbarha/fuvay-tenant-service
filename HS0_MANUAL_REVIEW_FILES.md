# HS0 — Files Requiring Manual Review

These items were noticed during HS0 but their disposition couldn't be
confidently determined within this sprint's scope. Flagged rather than
silently kept or deleted.

## Duplicate navigation source (architectural, not a file to delete)
Both frontends have **two parallel nav definitions**:
`lib/nav-config.ts` (a "Sprint 34K centralized" config, exported but not
actually imported by the live layout components) and the real,
live-rendered array hardcoded inside `components/layout/{Admin,Tenant}
Layout.tsx`. This sprint fixed the real duplicate-menu-item bug in the
live `TenantLayout.tsx` array and kept `nav-config.ts` in sync for
consistency, but the underlying architectural duplication (two sources
of truth for navigation) was not resolved. **Needs a decision**: either
retire `nav-config.ts` (if genuinely unused elsewhere) or refactor the
layout components to consume it (the originally-intended design per its
own header comment). Left as `REVIEW_MANUALLY`.

## 218 of 221 root-level markdown reports
Only the Home-Services-pricing/bargain lineage (a handful of files) was
reviewed for obsolescence this sprint (see `HS0_MD_FILE_CLEANUP_REPORT.md`).
The remaining ~215 files (Admin A1-A11, P0 Enterprise series, Sprint
1-38, Phase 0A-0E, etc.) were not individually assessed for
obsolescence/duplication — they were left as `KEEP` by default since
they document real certified work and are indexed in `MEMORY.md`, but a
dedicated documentation-cleanup sprint would be needed to confidently
classify all of them. Listed here as `REVIEW_MANUALLY` in aggregate
rather than hidden.

## `/admin/pricing` (city-tier floor price config)
Confirmed this is a legitimate, separate, vertical-agnostic page (not a
duplicate of Home Services Pricing Rules) — its own docstring says
"platform-wide city tier minimum prices." Kept as `KEEP`, but flagging
that its label ("Pricing Rules" in the sidebar `pricing` group) is close
enough to the Home Services "Pricing Rules" label that it could still
confuse an admin user. Not renamed this sprint (out of the ticket's
explicit forbidden-label list, which only targeted bargain/manual-pricing
terms) — `REVIEW_MANUALLY` for a future UX-clarity pass.

## `/admin/pricing-tiers`, `/admin/location-mapping`, `/admin/pricing/provider-overrides`
Present in the "Pricing & Rules" common admin group. Confirmed
vertical-agnostic (used across verticals, not Home-Services-specific)
per an explicit code comment in `AdminLayout.tsx`. Kept as `KEEP`, no
action needed, listed here only for completeness/transparency.
