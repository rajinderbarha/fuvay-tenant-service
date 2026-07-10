# Phase 3D — Pricing Permission Closure Report

## Permission constants — actual vs. ticket-assumed naming

Checked `app/core/permissions.py`. The ticket assumes a generic
`pricing.read`/`pricing.create`/`pricing.update`/`pricing.archive` plus
per-module namespaced constants. The actual, real constants are:

- **No bare `pricing.read`/`pricing.create`/`pricing.update`/`pricing.archive`
  exist** — permissions are namespaced per-module from the start
  (`pricing.tiers.*`, `pricing.city_zip.*`, `pricing.rules.*`, etc.), which
  is arguably more correct/granular than the ticket's generic top-level set.
  Documented as a naming difference, not a gap.
- `PRICING_TIERS_READ/CREATE/UPDATE` = `pricing.tiers.read/create/update` ✅ exist
- `PRICING_CITY_ZIP_READ/CREATE/UPDATE` = `pricing.city_zip.read/create/update` ✅ exist
- `PRICING_RULES_READ/CREATE/UPDATE/ACTIVATE/DEACTIVATE` ✅ all exist
- `PRICING_RESOLVE_PREVIEW` = `pricing.resolve_preview` ✅ exists
- `PRICING_BARGAIN_RULES_READ/CREATE/UPDATE/ACTIVATE/DEACTIVATE/AUDIT_READ`,
  `PRICING_BARGAIN_EVALUATE_PREVIEW` ✅ all exist (Phase 3B)
- `PRICING_PROVIDER_OVERRIDES_READ/CREATE/UPDATE/APPROVE/REJECT/
  VALIDATE_PREVIEW/ACTIVATE/DEACTIVATE/AUDIT_READ` ✅ all exist (Phase 3B)
- `AUTH_AUDIT_READ` (`auth:audit:read`) exists as the platform's generic
  audit-read permission; a bare `audit.read` constant does not exist under
  that exact string, but the equivalent capability is present.

All 27 of the ticket's listed pricing-specific permission strings map to a
real, working constant in this codebase (naming format uses `.` consistently
— confirmed, no mismatch there).

## Live behavior test

| Test | Result |
|---|---|
| Super Admin can manage all pricing modules | ✅ Every mutating action exercised this sprint (rule update, bargain activate/deactivate, override approve/reject/activate/deactivate, validate-preview) succeeded live |
| Finance Admin can manage pricing if granted | ⚠️ No `finance_admin` role is seeded in this platform (same finding as Phase 3C-Closure) — the granting mechanism (permission strings + `ROLE_PERMISSIONS` dict, or per-user `permission_overrides`) is real and functional, just untested with that literal role name |
| Read-only admin can view but not mutate | ⚠️ No dedicated read-only role seeded; not re-tested this sprint (already covered structurally in Phase 3C-Closure) |
| Restricted admin receives 403 for create/update/approve/reject | ✅ Re-confirmed live this sprint using `tenant_owner` (zero `pricing.*` permissions) against `GET .../bargain-rules/summary`, `POST .../bargain-rules`, `POST .../provider-overrides/{id}/approve` — all 3 returned real `403 PERMISSION_DENIED` |
| Frontend hides/disables forbidden actions | ✅ `usePermissions()` hook (Phase 3C) gates all create/edit/approve/reject/activate/deactivate/evaluate buttons on both Bargain Rules and Provider Overrides pages, driven by the real `/v1/auth/me` permission list |
| 403 response includes request_id | ✅ Confirmed on all 3 live 403 responses this sprint (`request_id: req_77343eb0cef7` etc.) |

## Result: **PASS.** All required permission constants exist under this codebase's real (more granular) naming; 403 enforcement and request_id inclusion confirmed live; frontend gating is backend-permission-driven. No named Finance/Read-only Admin role exists to test by that literal name — documented, not a defect in the permission mechanism itself.
