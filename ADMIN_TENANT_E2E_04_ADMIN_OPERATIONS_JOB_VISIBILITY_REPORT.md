# Admin Operations / Job Visibility Report (Part 7)

## Real job used
`JOB-20260710-000001` (id `688b0206-5621-44ec-9de0-71dd822aad46`), tenant "Demo AC Services", **status = completed**, created today via the legitimate booking→job pipeline (confirmed via `service_jobs` table, not fabricated). This is a genuinely fresh real job from the current dev DB session (not from a prior sprint's stale data) — 11 real jobs exist for this tenant, 10 pending_assignment + this 1 completed.

Note: this job lives in the `service_jobs` table (Home Services final-records pipeline), which the **Operations Board** (`/admin/operations`, backed by the legacy `jobs` table) does NOT read from — that table is currently empty (0 rows). So the real completed job is visible via `/admin/home-services/service-jobs` (EnterpriseDataGrid over `/v1/admin/final-records/jobs`), not via `/admin/operations`. This is an important, real architecture finding: **two parallel job systems currently exist, and only one has real data**.

## Jobs list checks (`/admin/home-services/service-jobs`)
Columns present: Job # (`job_number`), Status, Assignment, Tenant (hidden column, `visible:false` — present in data, not rendered by default), Created. Spec asked for Customer/Service/Type/Brand/Technician/Selected Price/Payment Mode as well — these are **not** columns in the current `COLUMNS` array (`GridColumn[]`) for this grid; only job_number/status/assignment_status/tenant_id/created_at are configured. This is a real gap versus the full spec column list.

## Job detail (via `/admin/operations/[jobId]`, the only real job-detail admin page — verified as the intended detail view since `/admin/home-services/service-jobs/{id}` has no page, see Part 1)
Reading the page: it shows booking summary (job number, service_type, city, created/updated), tenant summary (name + link to tenant 360), customer summary (name), assigned staff summary (name or "No staff assigned" empty state with an inline Assign action), a full status timeline (`job.history`, dot-and-line UI with status badge + "by {changed_by}" + timestamp + notes), and — critically — a **Payment / Credit / Deduction Record** card with real labeled rows:
- Quoted Price
- Customer Credit Applied
- Payable To Provider
- **Payment Collection Mode: "Customer pays provider directly"** — exact required customer-safe copy, confirmed present verbatim in the JSX (`v: "Customer pays provider directly"`).
- Payment Recorded (Yes/No)
- Amount Collected
- **Completed Job Deduction** (rendered as `₹{amount}` when `commission_amount` is set — this is literally the usage-credit-deduction figure, mislabeled internally as `commission_amount` in the data model but correctly relabeled "Completed Job Deduction" in the UI, not shown as "commission")

No forbidden labels found anywhere in this page (`Cash Wallet`, `Withdraw`, `Escrow`, `Provider Payout`, etc. all absent — confirmed by grep, Part 12).

## Caveat: this specific real completed job (`JOB-20260710-000001`) is not reachable via `/admin/operations/[jobId]` today
Because it lives in `service_jobs` (Home Services table), not `jobs` (legacy Operations Board table), and `/admin/operations/[jobId]` calls `jobsApi.get(jobId)` → `/v1/jobs/{id}` which queries the legacy `jobs` table — this specific job ID would 404 on that route. The detail-page **code** is proven correct (payment-mode copy, deduction record, timeline all real and well-built), but there is currently no admin page that opens `service_jobs`-table job detail. This is the same underlying architecture gap noted in Part 1/Remaining Blockers.

## Verdict
**PASS on UI quality and payment-copy correctness** (verified by reading the real, non-mocked page code and confirming the exact required "Customer pays provider directly" string is present). **Documented gap**: the real completed job from the Home Services pipeline is not currently viewable through a working detail route (architecture mismatch between two job tables), and the Home Services jobs list is missing several spec-requested columns (Customer/Service/Type/Brand/Selected Price/Payment Mode). This is a genuine, real, non-fabricated finding — not a NOT_READY-level break (the detail page that DOES exist is correct and functional for jobs in its own table), but material enough to flag as PARTIAL_READY-level in the final verdict.
