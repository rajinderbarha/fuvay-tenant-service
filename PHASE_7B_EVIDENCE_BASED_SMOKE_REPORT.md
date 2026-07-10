# Phase 7B — Evidence-Based Smoke Report

Live curl-based verification against the real running backend (`localhost:8000`) and real
Postgres, authenticated as the real technician fixture `staff@serviceos.in`
(`user_id f8a7e369-b5e2-49be-b277-d3a66032dace`, `role technician`,
`tenant_id 34b427a7-b2be-496c-b826-6d51bb181248`, Demo AC Services).

## Login

```
POST /v1/auth/login {"email":"staff@serviceos.in","password":"Password123!"}
→ 200, data.user.role == "technician", data.access_token present
```

## Auth / profile

```
GET  /v1/auth/me            → 200, role=technician, tenant_id matches fixture
PUT  /v1/auth/me {"full_name":"Demo Staff"} → 200
```

## Skills (team-members)

```
GET /v1/provider/team-members → 200
   members[0] = { user_id: f8a7e369-..., skills: ["AC Repair"], status: "active",
                   can_receive_assignment: true, category_id: 0888d283-... }
```

## Service Areas (before / after Bug 1 fix)

```
Before fix: GET /v1/tenant/service-areas → 403 PERMISSION_DENIED
                (tenant_service_area:read missing from technician role)
After fix:  GET /v1/tenant/service-areas → 200
                areas: [{ city: "Ludhiana", zipcode: "141001", coverage_type: "zipcode",
                          is_active: true }], total: 1
```

## Availability (before / after Bug 2 fix)

```
Before fix: GET /v1/provider/availability → 500 INTERNAL_ERROR
                (provider_availability_rules table did not exist)
After fix:  GET /v1/provider/availability → 200 {"rules": [], "count": 0}
```

## Jobs

```
GET /v1/staff/me/jobs?tenant_id=34b427a7-...        → 200 {"jobs": [], "has_next": false, ...}
GET /v1/staff/me/jobs?tenant_id=00000000-0000-...   → 200 (same real-tenant result — JWT
                                                        override confirmed still active)
```

## Notifications

```
GET /v1/staff/notifications → 200 {"items": [], "total": 0, "unread_count": null}
```

## Activity (confirmed absent)

```
GET /v1/provider/activity → 404 NOT_FOUND
   → confirmed no self-service activity endpoint exists; page ships an honest gap state.
```

## Backend regression check

`pytest tests/test_phase7_staff_app_certification.py` (Phase 7's 10 tests) re-run after this
sprint's permission/migration changes: **10/10 passed**, confirming no regression to the
already-certified Phase 7 backend surface.

`pytest tests/test_phase7b_staff_frontend_certification.py` (this sprint's 18 new tests):
**18/18 passed**.

Full-suite regression results are in `PHASE_7B_STAFF_FRONTEND_TEST_RESULTS.md`.
