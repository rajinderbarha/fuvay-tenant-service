# UX-08 Branch, Worktree and Baseline

- Branch: `design/ux-08-program-consolidation`
- Worktree: `G:/serviceos-ux08-program-consolidation`
- Created from: `50fe95b` (final UX-07 commit, `design/ux-07-cross-app-production-readiness`)
- HEAD at baseline freeze: `50fe95b`
- Working tree at baseline freeze: clean

## Ancestry verification (real `git merge-base --is-ancestor` output)

```
$ git merge-base --is-ancestor 7488335 HEAD ; echo $?
IS ancestor   (exit 0)

$ git merge-base --is-ancestor 493a132 HEAD ; echo $?
IS ancestor   (exit 0)

$ git merge-base --is-ancestor b426e08 HEAD ; echo $?
IS ancestor   (exit 0)
```

All three previously-approved baselines — UX-04 (`7488335`), UX-05
(`493a132`), UX-06 (`b426e08`) — are confirmed real ancestors of the UX-08
starting commit `50fe95b`. This matches the ancestry work already done and
documented during UX-07 Round 1 (`design/ux-07-cross-app-production-readiness`
was created from `design/ux-05b-finalization` @ `493a132`, which already
contains `7488335` as an ancestor, then `b426e08` was merged in cleanly).

**No baseline conflict.** `UX08_BASELINE_CONFLICT` does not apply.

## Environment at baseline freeze

- Backend: FastAPI, intended at `http://localhost:8000` / `http://172.28.240.1:8000` from WSL — reachability re-checked per-workstream below, not assumed.
- Database: PostgreSQL via `G:\serviceos\db\pgsql\bin\psql.exe`.
- Frontend toolchain: WSL Debian (root) for all install/build/test — native Windows npm remains broken (documented since UX-01).
- Node/npm versions: pinned per each app's own `package.json`/lockfile; no global drift permitted (see `package-config-drift-report.md`).

## Worktrees NOT touched by UX-08

`G:/serviceos` (shared main tree), `G:/serviceos-ux05b-finalization`,
`G:/serviceos-ux06-customer-app`, `G:/serviceos-ux07-cross-app`,
`G:/serviceos-phase2f-recovery`, `G:/serviceos-phase2f38-certification`,
`G:/serviceos-phase2f39-remediation`.
