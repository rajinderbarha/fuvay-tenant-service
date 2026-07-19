# Build Command Manifest

Once npm install succeeds on a working environment, run in order:

```
npm install --no-audit --no-fund
npm --workspace frontend/packages/design-system run build
npx tsc -p frontend/tenant-portal/tsconfig.json --noEmit
npm --workspace frontend/tenant-portal run build
npm --workspace frontend/super-admin run build   # non-regression check only
```
