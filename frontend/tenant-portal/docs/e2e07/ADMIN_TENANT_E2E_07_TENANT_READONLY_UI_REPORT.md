# E2E-07 Tenant Read-Only UI Report
**Date:** 2026-07-10  
**Analysis:** Static analysis — component created this sprint

---

## Summary

A `ReadOnlyBanner` component was created during this sprint as a standard read-only UI affordance.

## Component Created

**File:** `components/shared/ReadOnlyBanner.tsx`

### API

```tsx
import ReadOnlyBanner, { isReadOnly } from "../../components/shared/ReadOnlyBanner";

// Usage:
<ReadOnlyBanner role={me?.role} />

// Guard helper:
if (isReadOnly(role)) { /* disable mutation buttons */ }
```

### Role Detection

The `isReadOnly(role)` helper returns `true` for:
- `tenant_read_only`
- `read_only`
- Any role ending in `_viewer`

### Visual Design

- Amber/warning color band using CSS variables (`--warning-bg`, `--warning-border`, `--warning-text`)
- Eye icon from lucide-react
- Message: "View-only mode. Your account has read-only access. Contact your administrator to request write permissions."
- Auto-hides when role is null/undefined/write-enabled

## Pre-existing Read-Only Guards

| Check | Finding |
|---|---|
| Pre-existing `isReadOnly` logic in pages | None found before this sprint |
| Role field on `authApi.me()` response | YES — `TenantUser.role: string` |
| Backend RBAC enforcement | YES — backend enforces permissions; UI is informational |

## Adoption Status

The `ReadOnlyBanner` component is now available for use. Individual pages can import it and pass `me?.role` from `authApi.me()`. The component is self-hiding when role is write-enabled, so it is safe to add to any page.

**Integration recommendation:** High-mutation pages (Finance, Staff, Profile, Service Setup) should import `ReadOnlyBanner` in a follow-up sprint.

**Status: COMPONENT CREATED** — Available at `components/shared/ReadOnlyBanner.tsx`. Full page-level integration is a follow-up action.
