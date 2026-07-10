# Tenant Home Services Setup — Remaining Blockers

## P0 Blockers

None.

## P1 Items (Non-blocking)

### 1. Visual Range Slider (CSS only)
The pricing step shows a visual range bar as a CSS-positioned div fill. This is not an interactive
drag slider — it is a visual indicator only. Users type values into min/max inputs.

A proper `<input type="range">` dual-handle slider was not used because the shared `Input` component
does not support range inputs, and inline range inputs require custom CSS that can conflict with
theme variables.

**Mitigation:** Min/Max number inputs + visual bar gives clear UX without risk.

### 2. `homeServicesSetupApi` endpoint naming diverges from spec
The spec listed routes like `/v1/tenant/home-services/catalog/available`. The actual backend uses
`/v1/tenant/catalog/home-services/available-services`. All documented in API mapping report.

### 3. Brand override persisted without type scoping
`setBrandPricing(id, brandId, min, max)` does not pass a `serviceTypeId`. The backend endpoint
supports optional `?service_type_id=` scoping. Current implementation sets brand prices globally
(not per-type). This is correct for services with a single type but may produce unexpected behavior
for multi-type services with brand overrides.

**Recommended future fix:** In the brands step, ask tenant to select which type the brand override
applies to, then pass `serviceTypeId`.

## P2 Items (Nice-to-have)

### 1. Animated step transitions
Current step navigation is instant. CSS transitions between wizard steps would improve UX.

### 2. Draft auto-save
Currently draft is only saved on explicit "Save Draft" click. Auto-save on step advance could
prevent data loss if browser closes.

### 3. Service area count inline in wizard
The wizard checks `hasActiveArea` but does not show how many areas are configured. Showing
the count in the overview step would help tenants.
