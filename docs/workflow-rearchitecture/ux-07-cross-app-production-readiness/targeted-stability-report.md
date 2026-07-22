# Targeted Stability Report

Environment: fresh WSL Debian (root) install at
`/root/serviceos-ux07-verify-p3b/customer-app`, `npm install --legacy-peer-deps
--no-audit --no-fund` completed cleanly (540 top-level `node_modules`
entries) prior to these runs.

## Targeted test — 25 consecutive runs

Command per iteration:
```
npx jest ThemeContext.test.tsx -t "defaults to system preference"
```

Result: **25/25 passed**, 0 failures, no retries used.

## Full ThemeContext.test.tsx suite — 10 consecutive runs

Command per iteration:
```
npx jest ThemeContext.test.tsx
```

Each run required (and got) `5 passed, 5 total`.

Result: **10/10 runs fully green**, 0 failures, no retries used.
