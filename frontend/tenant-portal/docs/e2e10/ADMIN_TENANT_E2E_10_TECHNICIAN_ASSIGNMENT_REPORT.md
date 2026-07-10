# ADMIN-TENANT-E2E-10 — Technician Assignment Report

## Static Analysis Only

## File: `app/(tenant)/service-jobs/[id]/page.tsx`

## Assignment Flow

### States
| assignment_status | canAssign | canCancel | canSchedule |
|-----------------|-----------|-----------|-------------|
| `unassigned` | ✓ | ✗ | ✗ |
| `rejected` | ✓ (Reassign) | ✗ | ✗ |
| `assigned` | ✗ | ✓ | ✓ |
| `accepted` | ✗ | ✗ | ✓ |
| `cancelled` | ✗ | ✗ | ✗ |
| `scheduled` | ✗ | ✗ | ✗ |

### Assign Modal
- Fetches `getEligibleStaff(id)` on open (lazy, not on mount)
- Dropdown of eligible technicians
- Optional: scheduled date, time window, notes
- "Assign" button disabled until `staffId` is selected
- Success: `doAssign` → `serviceJobAssignmentApi.assign(id, payload)`
- Refetches context + timeline on success

### Schedule Modal
- Inputs: date (required), time window (required)
- Button disabled until both provided
- API: `serviceJobAssignmentApi.schedule(id, { scheduled_date, scheduled_time_window })`

### Cancel Assignment Modal
- Reason input (required)
- Button disabled until reason non-empty
- API: `serviceJobAssignmentApi.cancelAssignment(id, reason)`
- Returns job to `unassigned` status

## Assignment Timeline
- Events loaded from `serviceJobAssignmentApi.getTimeline(id)`
- Rendered as chronological list with event labels

## Issues Found
- Minor: hardcoded hex colors (`#111`, `#888`, `#333`, `#fef2f2`, `#f9fafb`) in card/dl elements
- These violate the design-token rule but do not affect functionality
- No fix applied (pre-existing, not a runtime blocker)

## Status: FUNCTIONAL PASS (style debt noted)
