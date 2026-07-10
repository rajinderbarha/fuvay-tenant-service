# ADMIN-TENANT-E2E-10 — Tenant Job Detail Report

## Static Analysis Only

## File: `app/(tenant)/jobs/[id]/page.tsx`

## Sections Present

### Hero Card
- Job number, `<JobStatusBadge>`, job type badge (REPAIR / SERVICE / CONSULTATION)
- Server-resolved allowed_transitions rendered as action buttons
- "Close Job ✓" button when `closed` is in allowed transitions
- "Spawn Repair →" for consultation jobs when appropriate

### Customer Card
- Name, phone, address
- "Open Chat →" ghost button → `/chat`

### Job Info Card
- Assigned staff, value, duration estimate, internal notes

### Payment Collection Card
- Shown when `quoted_price != null`
- Shows: Service Price, ServiceOS Credit Applied, Payable To Provider, Payment Mode, Amount Collected, Payment Recorded
- Payment Mode label: **"Customer pays provider directly"** ✓

### Usage Credit Deduction Card
- Shown when `commission_amount != null`
- Shows deduction amount
- Disclaimer: "Provider usage credits are not real money and are not withdrawable."

### Assessment / Findings Card (Repair + Consultation only)
- Visible only in ASSESSMENT_STATUSES set
- Edit Findings modal with findings + recommendation fields
- Disabled "Save Findings" until `findingsText.trim()` is non-empty ✓

### Service Checklist (Service jobs)
- Checkbox list with live toggle via `jobsApi.updateChecklist()`
- Progress counter badge

### Quotes Section (Repair + Consultation only)
- Lists all quotes with status, parts, labour, expiry
- "Send Quote" / "Send Report + Quote" button
- Re-assess flow on quote rejection

### Job Photos Card
- Before/After photo sections using `MediaUploader` and `MediaGallery`
- Loads via `mediaAssetApi.listAssets()`

### Status Timeline
- `jobsApi.history(id)` → `/v1/jobs/{id}/timeline`

## Modals Present
1. Status Update modal — notes optional, Confirm button
2. Close Job modal — final price input, credit deduction disclaimer
3. Send Quote modal — parts, labour, notes, expiry; disabled if `quoteTotal <= 0`
4. Findings modal — disabled until findings text non-empty

## Issues Found
- None. All API calls use `jobsApi.*` / `quotesApi.*` through `apiFetch`.

## Status: PASS
