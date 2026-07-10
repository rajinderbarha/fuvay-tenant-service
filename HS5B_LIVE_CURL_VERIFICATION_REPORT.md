# HS5B — Live Curl Verification Report

All 12 required scenarios executed against the real running backend
and real Postgres dev DB, using the real seeded tenant "Demo AC
Services" and real AC Repair/Split AC/LG catalog data.

## 1. Save valid break/lunch time
```
POST /v1/provider/availability {day:2, start:"09:00", end:"19:00", break_start:"14:00", break_end:"15:00"}
→ 200, created with break fields persisted correctly
```

## 2. Reject break outside working hours
```
POST /v1/provider/availability {day:3, start:"09:00", end:"19:00", break_start:"20:00", break_end:"21:00"}
→ 422 INVALID_BREAK_TIME_RANGE, "Break time must be inside working hours."
```

## 3. Create full-day holiday
```
POST /v1/provider/availability/exceptions {date:"2026-08-15", reason:"Independence Day", full_day_closed:true}
→ 201 (after fixing a real date-binding bug found during this test — see Exceptions report)
```

## 4. Create partial-day exception
```
POST /v1/provider/availability/exceptions {date:"2026-08-20", reason:"Team training", full_day_closed:false, start:"09:00", end:"13:00"}
→ 201, created correctly
```

## 5. Reject invalid exception time
```
POST /v1/provider/availability/exceptions {start:"15:00", end:"09:00"}
→ 422 INVALID_EXCEPTION_TIME_RANGE
```

## 6. Save booking-window settings
```
PUT /v1/provider/booking-window {120, 7, 60, 30}
→ 200, all fields persisted, matches ticket's exact defaults
```

## 7. Reject invalid slot duration
```
PUT /v1/provider/booking-window {slot_duration_minutes: 0}
→ 422 INVALID_SLOT_DURATION
```

## 8. Save per-area Split AC + LG coverage
```
PUT /v1/provider/service-areas/{ludhiana_central}/coverage {service:AC Repair, type:Split AC, brand:LG}
→ 200, real row created with service_type_id/brand_id persisted
```

## 9. Reject brand not valid for selected type
```
PUT /v1/provider/service-areas/{area}/coverage {service:AC Repair, type:Split AC, brand:<fake-uuid>}
→ 422 INVALID_BRAND_FOR_COVERAGE
```

## 10. Matching-input preview blocks request during lunch/break
```
POST /v1/provider/home-services/matching-inputs/preview {..., requested_at:"2026-07-14T14:30:00Z"}
→ is_bookable:false, blocked_by_break:true, all coverage checks true (isolating the block to time)
```

## 11. Matching-input preview blocks request during holiday
```
POST /v1/provider/home-services/matching-inputs/preview {..., requested_at:"2026-08-15T10:00:00Z"}
→ is_bookable:false, blocked_by_exception:true, real reason ("...Independence Day")
```

## 12. Matching-input preview allows valid service/type/brand/zipcode/time
```
POST /v1/provider/home-services/matching-inputs/preview {..., requested_at:"2026-07-14T11:00:00Z"}
→ is_bookable:true, blocking_reasons:[]
```

## Verdict
All 12 required live scenarios passed. One real bug (date-binding in
the exceptions endpoint) was found and fixed mid-verification, then
re-tested successfully.
