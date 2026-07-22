# Baseline Freeze Evidence

Frozen before any edit in this slice:

- Canonical CSV hash: `af8388463ac3dbfa`
- Matrix CSV hash: `3066e137e9a23c19`
- Protected/denominator/unprotected: 233/262/29
- The 5 residual routes' `guard_status`: all `PERMISSION_ONLY_NOT_SCOPE_AWARE`

These are the exact starting values recorded in
[residual-scope-freeze.md](residual-scope-freeze.md), captured by reading
the live canonical CSV directly (not from memory) before any Write/Edit
call in this slice touched it.
