# Global Coverage Reconciliation

## Starting provisional baseline
**190 protected of 226** tenant-facing mutations (Slice 2F-17).

## Full-application evidence gathered this slice
- 1186 total mounted mutation-method routes application-wide.
- 226 canonical CSV rows, ALL confirmed mounted at runtime (0 disconnected).
- Exactly 2 tenant-prefixed routes exist outside the canonical CSV, BOTH confirmed pre-existing false positives (0 genuinely missing).
- 3 whole-application duplicate `(method, path)` registrations, ALL platform-admin, 0 tenant-relevant.
- 0 canonical rows with a customer/admin/internal path prefix (0 misclassified rows).

## Exact arithmetic
```
Previous protected numerator:                 190
+ missing already-protected tenant mutations:   +0   (none found -- see missing-tenant-mutations.csv)
+ corrected protected classifications:          +0   (none needed -- 2F-17 already corrected the 4 stale
                                                        invoice_payment rows; no further correction found)
- protected rows removed as non-tenant/
  duplicate/false-positive/disconnected:         -0   (none found)
= final protected numerator:                   190

Previous tenant denominator:                  226
+ missing mounted tenant mutations:             +0   (zero found -- both candidates were false positives)
- customer routes:                              -0   (none present)
- platform/admin/internal routes:                -0   (none present)
- false positives:                               -0   (the one known false positive was already removed
                                                        in Slice 2F-17; no new one found)
- duplicates:                                    -0   (none tenant-relevant)
- deprecated routes:                             -0   (none found)
- disconnected routes:                           -0   (none found)
= final tenant denominator:                    226
```

## Final global figures — CONFIRMED, not merely provisional
**190 protected of 226 tenant-facing mutations.**

| Category | Count |
|---|---|
| Protected tenant mutations | 190 |
| Unprotected tenant mutations | 36 |
| Customer self-service mutations (tracked per-module: Booking 3 + quote_checklist 3) | 6 (partial — see `known-limitations.md` for the full-application customer-route count caveat) |
| Platform-admin mutations (application-wide) | 526 (487 `PLATFORM_ADMIN_ONLY` + 39 `CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES`) |
| Platform-internal mutations | 0 confirmed distinct from platform-admin (no separate bucket exists in this codebase) |
| Worker mutations | 0 (no internal-worker-only route found) |
| Public mutations | 39 |
| False positives (application-wide) | 10 |
| Deprecated routes | 0 |
| Duplicate runtime mounts (application-wide) | 3 (none tenant-relevant) |
| Disconnected canonical rows | 0 |

## One exact tenant X/Y
**190/226.** No headline convention or mixed denominator is used anywhere in this slice's documentation.
