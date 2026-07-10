# ADMIN-TENANT-E2E-10 — Tenant Jobs API Contract Report

## Static Analysis Only

## Jobs API (`lib/api.ts` lines 220–270)

| Method | HTTP | Endpoint | Used In |
|--------|------|----------|---------|
| `jobsApi.list(params)` | GET | `/v1/jobs?{qs}` | jobs/page.tsx |
| `jobsApi.get(id)` | GET | `/v1/jobs/{id}` | jobs/[id]/page.tsx |
| `jobsApi.history(id)` | GET | `/v1/jobs/{id}/timeline` | jobs/[id]/page.tsx |
| `jobsApi.updateStatus(id, status, notes)` | PUT | `/v1/jobs/{id}/status` | jobs/[id]/page.tsx |
| `jobsApi.updateChecklist(id, items)` | PUT | `/v1/jobs/{id}/checklist` | jobs/[id]/page.tsx |
| `jobsApi.slaAlerts()` | GET | `/v1/jobs/sla-alerts` | jobs/page.tsx |
| `jobsApi.close(id, notes)` | POST | `/v1/jobs/{id}/close` | jobs/[id]/page.tsx |
| `jobsApi.recordPayment(id, amount)` | POST | `/v1/jobs/{id}/record-payment` | (available, not in UI) |
| `jobsApi.getTransitions(id)` | GET | `/v1/jobs/{id}/transitions` | (available) |
| `jobsApi.voidJob(id, reason)` | POST | `/v1/jobs/{id}/void` | (available) |
| `jobsApi.addNote(id, content, ...)` | POST | `/v1/jobs/{id}/notes?tenant_id=` | (available) |
| `jobsApi.listNotes(id)` | GET | `/v1/jobs/{id}/notes` | (available) |
| `jobsApi.slaStatus(id)` | GET | `/v1/jobs/{id}/sla` | (available) |
| `jobsApi.counts(tid)` | GET | `/v1/jobs/tenants/{tid}/counts` | (available) |
| `jobsApi.spawnRepair(id)` | POST | `/v1/jobs/{id}/spawn-repair` | jobs/[id]/page.tsx |

## Quotes API (`lib/api.ts` lines 418–430)

| Method | HTTP | Endpoint | Used In |
|--------|------|----------|---------|
| `quotesApi.listByJob(jobId)` | GET | `/v1/jobs/{jobId}/quotes` | jobs/[id]/page.tsx |
| `quotesApi.create(jobId, amount, parts, ...)` | POST | `/v1/jobs/{jobId}/quote` | jobs/[id]/page.tsx |
| `quotesApi.respond(quoteId, accepted)` | POST | `/v1/jobs/quotes/{quoteId}/respond` | (customer-side) |
| `quotesApi.submitFindings(jobId, findings, rec)` | POST | `/v1/jobs/{jobId}/findings` | jobs/[id]/page.tsx |

## Service Job Assignment API

| Method | HTTP | Endpoint | Used In |
|--------|------|----------|---------|
| `serviceJobAssignmentApi.getContext(id)` | GET | `/v1/provider/service-jobs/{id}` | service-jobs/[id]/page.tsx + execution |
| `serviceJobAssignmentApi.getEligibleStaff(id)` | GET | `/v1/provider/service-jobs/{id}/eligible-staff` | service-jobs/[id]/page.tsx |
| `serviceJobAssignmentApi.getTimeline(id)` | GET | `/v1/provider/service-jobs/{id}/timeline` | service-jobs/[id]/page.tsx |
| `serviceJobAssignmentApi.assign(id, payload)` | POST | `/v1/provider/service-jobs/{id}/assign` | service-jobs/[id]/page.tsx |
| `serviceJobAssignmentApi.schedule(id, payload)` | POST | `/v1/provider/service-jobs/{id}/schedule` | service-jobs/[id]/page.tsx |
| `serviceJobAssignmentApi.cancelAssignment(id, reason)` | POST | `/v1/provider/service-jobs/{id}/cancel-assignment` | service-jobs/[id]/page.tsx |

## Execution API

| Method | Endpoint |
|--------|----------|
| `homeServiceExecutionApi.getProviderTimeline(id)` | `/v1/provider/service-jobs/{id}/execution/timeline` |
| `homeServiceExecutionApi.getNotes(id)` | `/v1/provider/service-jobs/{id}/execution/notes` |
| `homeServiceExecutionApi.listPartsRequests(id)` | `/v1/provider/service-jobs/{id}/parts-requests` |
| `homeServiceExecutionApi.approveParts(jobId, prId)` | POST `/v1/provider/service-jobs/{id}/parts/{pr_id}/approve` |
| `homeServiceExecutionApi.rejectParts(jobId, prId, reason)` | POST |
| `homeServiceExecutionApi.onTheWay(id)` | POST |
| `homeServiceExecutionApi.reachedSite(id)` | POST |
| `homeServiceExecutionApi.startInspection(id)` | POST |
| `homeServiceExecutionApi.completeInspection(id)` | POST |
| `homeServiceExecutionApi.startService(id)` | POST |
| `homeServiceExecutionApi.workDone(id)` | POST |
| `homeServiceExecutionApi.quoteRequired(id, note)` | POST |
| `homeServiceExecutionApi.cancel(id, reason)` | POST |
| `homeServiceExecutionApi.addNote(id, text)` | POST |

## Status: PASS — All job API calls use apiFetch, no direct fetch() in job pages
