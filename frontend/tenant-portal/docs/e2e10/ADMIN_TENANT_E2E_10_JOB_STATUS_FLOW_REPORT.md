# ADMIN-TENANT-E2E-10 — Job Status Flow Report

## Static Analysis Only

## Architecture: Server-Resolved Transitions

The tenant portal does NOT maintain a frontend copy of the status graph. Instead:
- `jobs/[id]/page.tsx` reads `j.allowed_transitions` from the API response
- The backend returns job_type-aware allowed transitions per job
- UI buttons are generated from `allowedTransitions` array dynamically

## Status Transition Buttons
```
allowedTransitions
  .filter(s => !["invoice_generated","closed"].includes(s))
  .slice(0, 4)
  → Btn variant: "danger" if cancelled/voided, "success" if work_complete/quality_passed, else "secondary"

allowedTransitions.includes("closed") → "Close Job ✓" button (success variant)
```

## Execution-Level Status Actions (`service-jobs/[id]/execution/page.tsx`)
Mapped statically in `STATUS_ACTIONS`:
| Current Status | Available Actions |
|---------------|-----------------|
| `accepted` | On the Way |
| `scheduled` | On the Way |
| `on_the_way` | Reached Site |
| `reached_site` | Start Inspection |
| `inspection_started` | Complete Inspection |
| `inspection_done` | Start Service, Quote Required |
| `service_started` | Work Done, Quote Required |

## Job Type Differentiation
| job_type | Quote Section | Assessment | Checklist | Spawn Repair |
|----------|--------------|-----------|-----------|-------------|
| repair | ✓ | ✓ | if present | ✗ |
| service | ✗ | ✗ | ✓ | ✗ |
| consultation | ✓ | ✓ | if present | ✓ |

## Close Job Flow
1. "Close Job ✓" button opens modal
2. Modal shows disclaimer: credits deducted, not real money, not withdrawable
3. Final price input (defaults to quoted_price)
4. `jobsApi.close(id, finalPrice)` → `POST /v1/jobs/{id}/close`

## Status: PASS — Server-driven transitions, no stale frontend state machine
