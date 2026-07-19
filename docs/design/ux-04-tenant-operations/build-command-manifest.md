# Build Command Manifest

All commands run from a WSL Debian native-filesystem copy
(`/root/serviceos-ux04`), synced from `G:\serviceos` via rsync (excluding
`node_modules`/`.next`), per the proven UX-03 install workaround.

```
npm install --workspaces --include-workspace-root --no-audit --no-fund   # from /root/serviceos-ux04
npx tsc --noEmit                                                          # from /root/serviceos-ux04/frontend/tenant-portal
npx next build                                                           # from /root/serviceos-ux04/frontend/tenant-portal
```

No vitest/jest config was found configured for `frontend/tenant-portal` to
run a UX-04-specific automated test suite this pass (see
`frontend-test-report.md`).
