# ADMIN-TENANT-E2E-10 — Customer Tracking Impact Report

## Static Analysis Only

## Customer-Facing Job Tracking

### Tenant Portal Does Not Show Customer Tracking URLs
The tenant portal itself does not display the customer tracking link or token. Tracking is a customer-app concern.

### `jobsApi.trackByToken` (lib/api.ts line 267)
```typescript
trackByToken: (token: string) => apiFetch<TrackedJob>(`/v1/jobs/track/${token}`)
```
- Endpoint exists in API layer but is not used in any tenant portal page
- This endpoint is intended for the customer-facing app

### Customer Impact Points in Tenant Portal

#### 1. Job Completion → Review Request
Close Job modal (`jobs/[id]/page.tsx`, line 558–563):
> "Closing this job will apply a Completed Job Deduction to your provider usage credits and send a review request to the customer."

#### 2. Chat Link in Job Detail
- "Open Chat →" button in Customer card → `/chat`
- Allows tenant to message the customer about the job

#### 3. Assignment Notifications
- When tenant assigns/schedules a technician, backend is expected to notify customer
- Frontend triggers: `serviceJobAssignmentApi.assign()` and `serviceJobAssignmentApi.schedule()`
- Notification delivery is backend-handled

#### 4. SLA Alerts (Tenant View)
- SLA overdue jobs highlighted in the jobs list
- Overdue rows shown in `var(--warning-bg)` background
- Alerts displayed above the table with severity badges

## Customer Experience Outcomes
| Tenant Action | Customer Impact |
|--------------|----------------|
| Assign technician | Customer notified (backend) |
| Schedule visit | Customer gets scheduled time |
| Technician "Work Done" | Status update to customer |
| Close Job | Review request sent to customer |
| Chat | Direct message to customer |

## Status: INFORMATIONAL — Tracking impact documented, no UI bugs found
