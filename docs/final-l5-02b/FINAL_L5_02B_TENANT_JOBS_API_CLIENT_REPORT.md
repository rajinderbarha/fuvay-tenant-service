# FINAL-L5-02B — Tenant Jobs API Client Report

`serviceJobsApi` and `serviceJobAssignmentApi` (both in `frontend/tenant-portal/lib/api.ts`, established in FINAL-L5-01D, reused unchanged this sprint) are the canonical typed client for Tenant Jobs.

```ts
serviceJobsApi.list(params?: { status?: string; limit?: number; offset?: number })
serviceJobsApi.get(jobId: string)

serviceJobAssignmentApi.listAssignable(params?)
serviceJobAssignmentApi.getContext(jobId)
serviceJobAssignmentApi.getEligibleStaff(jobId)
serviceJobAssignmentApi.assign(jobId, payload)
serviceJobAssignmentApi.cancelAssignment(jobId, reason)
serviceJobAssignmentApi.schedule(jobId, payload)
serviceJobAssignmentApi.getTimeline(jobId)
```

## Requirement compliance
1. **No raw endpoint strings in page components** — confirmed; all 4 consumer files (list, detail, dashboard widget, staff-detail widget) call typed `serviceJobsApi`/`serviceJobAssignmentApi` methods only.
2. **Auth handled centrally** — `apiFetch()` injects the Bearer token from `getToken()` on every call.
3. **Tenant context handled centrally** — tenant scoping is derived server-side from the JWT (`_get_tenant_id(user)`), not passed as a client parameter — no tenant ID leakage/spoofing surface.
4. **Query serialization handled centrally** — `URLSearchParams` construction lives inside `serviceJobsApi.list`, not duplicated per page.
5. **`request_id` preserved** — `apiFetch`'s error path attaches `err.request_id` to the thrown `ServiceOSError`, unchanged by this sprint's edits.
6. **401/403/404/409/422 handled consistently** — via `apiFetch`'s shared error-normalization path (`ServiceOSError` with `code`/`message`/`resolution`/`context`/`requestId`), same as every other typed API module.
7. **AbortSignal** — not currently threaded through `apiFetch`'s options for GETs in this codebase (a pre-existing, app-wide characteristic, not unique to Jobs); not introduced or removed this sprint.
8. **No unsafe automatic retry for mutations** — confirmed; `assign`/`cancelAssignment`/`schedule` are one-shot `apiFetch` POST calls with no client-side retry loop.

No new typed methods were needed this sprint — the existing `serviceJobsApi` shape already covered both new consumers (dashboard widget, staff-detail widget) without modification.
