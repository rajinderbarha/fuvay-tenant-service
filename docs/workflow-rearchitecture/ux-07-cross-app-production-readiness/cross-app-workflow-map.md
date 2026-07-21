# Cross-App Workflow Map — Round 1

## Proven this round (real, live)

```
customer (mobile/customer-app)
  -> POST .../booking-drafts ... -> POST .../confirm
  -> creates ServiceBooking (BK-20260721-000008) + ServiceJob (JOB-20260721-000008)
       |
       v
tenant_owner (tenant-portal, tenant 5209ef33-...)
  -> GET /v1/provider/service-jobs/assignable   (sees the same job)
  -> GET .../eligible-staff -> POST .../assign  (assigns real technician)
       |
       v
technician (mobile/staff-app, same tenant)
  -> GET /v1/staff/service-jobs                 (sees the same job, assigned)
  -> POST .../accept                            (real, legal status transition)
       |
       v
tenant-portal (refresh)      -> GET .../assignment-timeline shows the event
customer-app (refresh)       -> GET /v1/customer/bookings/{id} shows status:accepted
```

Single real ServiceBooking/ServiceJob pair, one pipeline (ServiceBooking ->
ServiceJob, the canonical Home Services pipeline per the domain rules),
identity preserved across all 3 apps -- no adaptation into field_ops.Job.

## Not yet mapped this round (deferred)

- Quote/checklist/parts/completion/commission/review continuation of this
  same job (Workstreams 7-8) -- the job currently sits at a real `accepted`
  status, a valid pickup point for a future round.
- Super-admin's view of this same tenant/job (no super_admin credential
  found this round -- see role-navigation-matrix.csv).
- Tenant onboarding, catalog/pricing continuity, error/recovery states
  (Workstreams 3, 4, 10) -- not attempted this round.
