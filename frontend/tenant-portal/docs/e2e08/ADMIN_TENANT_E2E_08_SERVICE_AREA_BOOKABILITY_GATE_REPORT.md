# ADMIN-TENANT-E2E-08: Service Area Bookability Gate Report

**Date:** 2026-07-10

## Bookability Gate Logic

The service area page enforces the following bookability gate in UI:

1. **At least one active area required** — `issues` array includes `severity: "danger"` entry when `totalActive === 0`. Action Required panel is shown with "Add Area" CTA.
2. **Primary area required** — `issues` array includes `severity: "warning"` when no primary area is set. CTA: "Set Primary".
3. **Slot limit enforcement** — add button disabled (`limitReached`), AreaWizard shows error banner when limit is reached.

## Detail Drawer Bookability Impact Section
Each area's drawer shows:
- Active: "This area is active and counts toward your bookability requirement."
- Inactive: "This area is inactive and does not count toward bookability."
- Last active warning: "Disabling or deleting this area will remove your only active service area and affect bookability."

## Delete Confirm
Shows "last active area" warning when `isLastActive = area.is_active && totalActive === 1`.

## Validation Preview
Server-side validation (`/validate` endpoint) returns:
- `resolved_city`, `resolved_district`, `resolved_state`, `resolved_zone_tier`
- `coverage_valid`, `is_duplicate`, `package_limit_ok`, `remaining_service_areas`
- `serviceable` (bool) + `bookability_impact` (message)

## Coverage Rules Sidebar
Three rules checked in real-time:
1. One primary area required
2. Maximum N service areas on current plan  
3. Active areas are visible for customer matching

## Gap
Backend bookability gate (whether the tenant is actually set as bookable) is read via `providerStatusApi.get()` but the bookability blockers from that API are not surfaced directly in the service areas page — they come from `stat?.visibility_blockers` and `stat?.bookability_blockers` which are only shown in the status/profile pages, not here. This is a minor UX gap, not a functional bug.
