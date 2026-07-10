# ADMIN-TENANT-E2E-10 — Technician Data Report

## Static Analysis Only

## Eligible Staff Data

### Source
`serviceJobAssignmentApi.getEligibleStaff(jobId)` → `GET /v1/provider/service-jobs/{id}/eligible-staff`

### Fields Used in UI
| Field | Usage |
|-------|-------|
| `staff_member_id` | Assign modal option value |
| `name` | Display name in dropdown |
| `role` | Shown in parentheses: `{name} ({role})` |

### Type Definition
```typescript
interface EligibleStaffRecord {
  staff_member_id: string;
  name: string;
  role: string;
}
```

## Technician Assignment Context
`serviceJobAssignmentApi.getContext(jobId)` → `GET /v1/provider/service-jobs/{id}`

Returns:
- `job`: job summary (job_number, status, assignment_status, city, scheduled_date, scheduled_time_window)
- `current_assignment`: assignment detail (status, type, scheduled_date, accepted_at, rejected_at, rejection_reason, notes)

## No Mock Technician Data
Grep for `mockTechnician`, `fakeTechnician` returned no results.

## Status: PASS — All technician data from live API
