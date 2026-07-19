# Build Command Manifest

Commands that WOULD be used to verify this phase, none of which were run to completion (MODE B):

```
# 1. Install
cd frontend/super-admin && npm install --no-audit --no-fund

# 2. Typecheck
npx tsc --noEmit

# 3. Tests (once vitest is added — see frontend-test-report.md)
npm run test

# 4. Production build
npm run build   # (next build)

# 5. Non-regression check for the shared design-system consumer
cd ../tenant-portal && npm install --no-audit --no-fund && npm run build
```

Each command's expected exit code is 0 with no errors. None have been observed to actually run
successfully in this environment — see `build-report.md` for the one attempt that was made
(the `npm install` in Step 0) and its exact failure.
