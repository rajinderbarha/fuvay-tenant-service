# ADMIN-TENANT-E2E-10 — Browser E2E Report

## STATIC ANALYSIS ONLY — No Browser Automation Available

No browser automation tools (Playwright, Cypress, Selenium) were available in this run. All verification was performed via static code analysis.

## Equivalent Manual Test Scenarios

### Scenario 1: Jobs Board
1. Navigate to `/jobs`
2. Expected: List loads from `GET /v1/jobs`, SLA alerts displayed, filter/search work client-side

### Scenario 2: Job Detail — Service Job
1. Navigate to `/jobs/{service_job_id}`
2. Expected: Customer card, Job Info, Payment Collection (mode: "Customer pays provider directly"), Checklist, Timeline

### Scenario 3: Job Detail — Repair Job
1. Navigate to `/jobs/{repair_job_id}`
2. Expected: Assessment card, Quotes section, "Send Quote" button, before/after photos

### Scenario 4: Technician Assignment
1. Navigate to `/service-jobs/{job_id}`
2. Click "Assign Technician"
3. Expected: Dropdown loads from `GET /v1/provider/service-jobs/{id}/eligible-staff`
4. Select technician, click Assign
5. Expected: POST to assign endpoint, context refetched, timeline updated

### Scenario 5: Job Execution
1. Navigate to `/service-jobs/{job_id}/execution`
2. Expected: Status action bar shows correct next actions, parts requests visible

### Scenario 6: Close Job
1. Navigate to `/jobs/{closeable_job_id}`
2. Click "Close Job ✓"
3. Expected: Modal opens with credit disclaimer, final price input
4. Confirm → `POST /v1/jobs/{id}/close`

### Scenario 7: Usage Credit Ledger
1. Navigate to `/finance/usage-credit-ledger`
2. Expected: Balance cards, ledger table with completed_job_deduction entries

## Evidence
Not available. Would require running backend at `localhost:8000` and browser session.

## Status: STATIC ANALYSIS COMPLETE — Browser testing pending live environment
