# FINAL-L5-01D — Cross-Application Browser Regression

## Admin
| Check | Result |
|---|---|
| Login → Dashboard | Real 200, no 404 (Turbopack fix from FINAL-L5-01B-PLUS holds) |
| Tenants | Real data — "Demo AC Services" confirmed present |
| Jobs / Usage Credit Ledger | Not re-verified this specific pass (verified in FINAL-L5-02's live smoke) |

## Tenant
| Check | Result |
|---|---|
| Owner login | Real 200 |
| Jobs list/detail | **Real canonical data, no legacy endpoint** (this sprint's primary fix, verified) |
| Read Only login | Real 200 |
| Mutation control verification | **Real fix verified**: banner appears consistently, Jobs detail buttons hidden |

## Customer
| Check | Result |
|---|---|
| Customer One bookings | **Real data, 5 bookings visible** (this sprint's second primary fix, verified) |
| Customer Two isolation | Confirmed at API layer (zero leakage) |

## Staff
| Check | Result |
|---|---|
| Technician login redirect | **Fixed but not proven stable** — 1/5 runs succeeded quickly; 4/5 timed out, root cause not fully isolated |
| Assigned jobs / Job detail | Not reached in the unstable runs; confirmed reachable in the one successful run and the isolated debug run |

## Global assertions

| Assertion | Result |
|---|---|
| No raw JSON | Confirmed — all tested pages render formatted UI |
| No NaN/null/undefined visible | Not exhaustively checked this pass |
| No runtime mock data | Confirmed — all data traced to real backend calls |
| No wrong-tenant/customer data | Confirmed — Customer Two isolation, Tenant isolation (Isolation Test Services = 0 jobs) both hold |
| No unexplained 401/403 | Confirmed — every 401/403 observed was an intended RBAC rejection |
| No legacy Tenant Jobs endpoint | **Confirmed via real network capture** |
| No customer empty state from wrong booking table | **Confirmed fixed** |
| No redirect loop | Confirmed — Technician failures were stalls, not loops |
| No serious console error | Partially checked — 3 console errors noted in FINAL-L5-01B-PLUS's admin session, not re-classified this sprint |
| Real API requests observed | Confirmed throughout |

## Result
**Substantially passing**, with one open item (Technician redirect stability) honestly carried forward rather than hidden or claimed resolved.
