# HS2B — Cards-First UI Report

## What was already done (HS2)
8 real, data-driven catalog health cards render immediately below the
page header, before any table or list — confirmed unchanged and still
present this sprint.

## What HS2B adds
- Provider Setup Rules tab (see dedicated report).
- Permission-aware 403 block state.
- "Add Service Group" and "View Audit" top actions.

## What remains NOT done (honest gap)
The ticket's full "cards-first" redesign asks for:
- Service **groups** displayed as cards/accordion sections with a
  group-level summary (services count, customer-visible count,
  provider-selectable count, setup-issues count, "Manage" CTA).
- Service **cards** (not rows) inside each group, each showing the
  ticket's exact 10-field list plus a distinct Setup Status badge
  (Ready/Needs Types/Needs Questions/Needs Brands/Inactive/Draft/
  Blocked).

**This was not built this sprint.** The left panel remains a compact
grouped row-list (`ServiceRow`), not a card grid. Rebuilding this into
true group-cards + service-cards is a substantial visual/layout change
(new components, new grid CSS, a group-level aggregation query or
client-side computation) that was deprioritized in favor of the other 5
blockers, all of which had clearer functional (not just visual)
acceptance criteria.

## Why this was the trade-off made
Given the sprint's time budget, the choice was between (a) a full visual
redesign of the service list with no functional change, or (b) closing
5 other blockers with real functional impact (Group CRUD linkage,
baseline audit, Provider Setup Rules tab, permission-aware UI,
delete-safety fix). (b) was judged higher value and was completed;
(a) remains open.

## Verdict
Cards-first redesign: **partially complete** (health cards done, service
list still row-based). This is the primary reason full `READY`
certification is not being claimed this sprint — see Remaining
Blockers.
