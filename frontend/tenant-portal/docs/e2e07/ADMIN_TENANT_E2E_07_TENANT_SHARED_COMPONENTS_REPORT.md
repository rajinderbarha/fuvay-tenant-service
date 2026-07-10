# E2E-07 Tenant Shared Components Report
**Date:** 2026-07-10  
**Analysis:** Static analysis

---

## Shared Components Inventory

### `components/shared/`

| Component | File | Purpose |
|---|---|---|
| `ReadOnlyBanner` | `ReadOnlyBanner.tsx` | NEW — shows read-only warning banner for restricted roles |
| Layout primitives | `layout.tsx` | `Page`, `Section`, `Stack`, `Row`, `Col`, etc. |
| UI primitives | `ui.tsx` | `Btn`, `Modal`, `Badge`, `Toaster`, `KpiCard`, etc. |
| `ApiStates` | `ApiStates.tsx` | Loading/error state wrappers |
| `ProfilePhotoUploader` | `ProfilePhotoUploader.tsx` | Profile photo upload + `DefaultAvatar` |

### `components/layout/`

| Component | File | Purpose |
|---|---|---|
| `TenantLayout` | `TenantLayout.tsx` | Main shell layout |
| `Breadcrumbs` | `Breadcrumbs.tsx` | URL-based breadcrumb generator |
| `StaffLayout` | `StaffLayout.tsx` | Staff sub-portal shell |

### `components/enterprise/`

| Component | File | Purpose |
|---|---|---|
| `EnterpriseDataGrid` | `EnterpriseDataGrid.tsx` | Paginated data table |
| `EnterpriseFilterBar` | `EnterpriseFilterBar.tsx` | Filter chips |
| `EnterprisePagination` | `EnterprisePagination.tsx` | Pagination controls |
| `EnterpriseColumnManager` | `EnterpriseColumnManager.tsx` | Column visibility |

### `components/dashboard/`

| Component | File | Purpose |
|---|---|---|
| `GenericDashboard` | `GenericDashboard.tsx` | Fallback dashboard |
| `HomeServiceDashboard` | `HomeServiceDashboard.tsx` | Home services KPIs |
| `CoachingDashboard` | `CoachingDashboard.tsx` | Coaching vertical |
| `RealEstateDashboard` | `RealEstateDashboard.tsx` | Real estate vertical |
| `OnboardingWidget` | `OnboardingWidget.tsx` | Onboarding progress |
| `BookabilityStatusWidget` | `BookabilityStatusWidget.tsx` | Bookability indicator |
| `MarketingLaunchWidget` | `MarketingLaunchWidget.tsx` | Marketing status |
| `MonetizationStatusWidget` | `MonetizationStatusWidget.tsx` | Monetization status |

### `components/media/`

| Component | File | Purpose |
|---|---|---|
| `MediaUploader` | `MediaUploader.tsx` | File upload UI |
| `MediaPreview` | `MediaPreview.tsx` | File preview |
| `MediaGallery` | `MediaGallery.tsx` | Gallery grid |

### `components/status/`

| Component | File | Purpose |
|---|---|---|
| `TenantStatusBadge` | `TenantStatusBadge.tsx` | Status chip |
| `TenantStatusHero` | `TenantStatusHero.tsx` | Hero status card |
| `TenantStatusActionCenter` | `TenantStatusActionCenter.tsx` | Action buttons |
| `TenantReadinessScoreCards` | `TenantReadinessScoreCards.tsx` | Score card grid |
| `TenantStatusPanels` | `TenantStatusPanels.tsx` | Panel collection |

### `components/analytics/`

| Component | File | Purpose |
|---|---|---|
| Analytics index | `analytics/index.tsx` | Analytics chart wrappers |

### `components/tour/`

| Component | File | Purpose |
|---|---|---|
| `TourGuide` | `TourGuide.tsx` | Step-by-step UI tour |

**Status: PASS** — All shared components present and accounted for. `ReadOnlyBanner` added this sprint.
