# ADMIN-TENANT-E2E-10 — Parts & Extra Cost Discovery Report

## Static Analysis Only

## Parts Request Flow (Home Service Execution)

### File: `service-jobs/[id]/execution/page.tsx`

#### Data Source
`homeServiceExecutionApi.listPartsRequests(jobId)` → `GET /v1/provider/service-jobs/{id}/parts-requests`

#### Parts Request Fields Displayed
| Field | Display |
|-------|---------|
| `part_name` | Part label |
| `quantity` | Shown as `× {quantity}` |
| `estimated_cost` | `₹{estimated_cost.toLocaleString("en-IN")}` |
| `reason` | Reason text |
| `status` | Color-coded badge: requested (blue), installed (green), rejected (red) |

#### Tenant Actions on Parts Requests
- **Approve**: `homeServiceExecutionApi.approveParts(jobId, partsRequestId)` — shown for `status === "requested"` only
- **Reject**: `homeServiceExecutionApi.rejectParts(jobId, partsRequestId, "Rejected by business")` — shown for `status === "requested"` only

#### Loading State
`partsActionLoading` tracks the specific `parts_request_id` being actioned — prevents double-click.

## Quote Required Flow
When technician clicks "Quote Required" (for `inspection_done` or `service_started`):
- Modal opens asking for quote description
- `homeServiceExecutionApi.quoteRequired(jobId, quoteNote)` called
- Modal button disabled until `quoteNote.trim()` is non-empty

## Extra Costs in Job Detail (`jobs/[id]/page.tsx`)
- Quote parts are listed in the Quotes section
- Each part shows name + cost
- Labour estimate shown separately
- Total calculated as `partsTotal + labourEstimate`

## Issues Found
- None. Parts management flow complete and connected to live API.

## Status: PASS
