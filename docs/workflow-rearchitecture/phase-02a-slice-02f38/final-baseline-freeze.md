# Final Baseline Freeze — Slice 2F-38

| Field | Value |
|---|---|
| Certification branch | `security/phase-2f38-certification` |
| Certification HEAD | `01e6ee4405490b0a90494b60d2472d4b1548ff66` |
| Parent commit | `d00f7230f98236c96dd21e1498c78779dc209e7b` (Slice 2F-37R-A) |
| Worktree | `G:/serviceos-phase2f38-certification` |
| Dirty files at freeze | 2 (this slice's own new guard script + state file, both untracked) |

## Hashes (SHA-256)

| File | Hash |
|---|---|
| `app/core/permissions.py` | `07a3139b1a1e1875aa11501f204b4f10767ab02258c32830e30b5ea68e7c1ec7` |
| `app/dependencies/auth.py` | `e8616b77a931f40fa3873aabc385ae49818e7837094bd402920533408280d935` |
| `alembic/versions/144_users_role_canonical_check.py` | `824c4ed292e709748879f79f11b9c479c5e9053a4d0d4f6b6061d99303da1f9d` |
| `docs/.../phase-02a-slice-02f37/canonical-coverage-arithmetic.csv` | `e34c6d95a51d255c013e3b5f2da9f0264aba1ceda81c3cfff4a30d77cdfe850c` |
| `docs/.../phase-02a-slice-02f37/mutation-enforcement-matrix-diff.csv` | `f06410cb4ba654649040cbc03bf821095defcaa877d0bf271b394e9407dfc87c` |
| `docs/.../phase-02a-slice-02f37/held-route-adjudication.csv` | `2a43cc527b4a0a1eabb917015bd98e409a3b1821eddbd9c37bccb28614d13c8a` |

Canonical inventory hash, enforcement-matrix hash and Set A/B/C frozen
hashes are independently re-derived at runtime by
`verify_2f37.py` (R01/R19/R20), not copied from documentation — see
`recovered-baseline-verification.md`.

## Environment availability

| Dependency | Status |
|---|---|
| PostgreSQL (`psql`/`pg_ctl`/`postgres` binaries) | **Not available** — not in PATH |
| `DATABASE_URL` / `POSTGRES*` / `REDIS*` env vars | **Not set** |
| Docker daemon | **Not running** — client v29.5.2 present, `docker version`/`docker ps` fail to connect to `npipe:////./pipe/dockerDesktopLinuxEngine` |
| Redis | Not independently checked; no evidence of availability, consistent with no reachable database stack |
| Worker processes | Not running (no live server process in this environment) |
| External services (Razorpay, storage, etc.) | Not available (unchanged from every prior slice in this program) |

This is unchanged from every prior investigation in Slices 2F-37R,
2F-37R-A, and the original (halted) 2F-38 attempt — re-verified fresh in
this dedicated worktree rather than assumed.

## Phase-2F collected node count

2445 (verified in `phase2f-regression-report.md`).

## Complete-backend collected node count

See `full-backend-regression-report.md`.
