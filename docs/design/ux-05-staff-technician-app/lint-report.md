# Lint Report

`package.json` has a `lint` script (`eslint src --ext .ts,.tsx`) but **no `eslint.config.js`/`.eslintrc.*` exists
in `mobile/staff-app`**. Running it in WSL:

```
npx eslint src --ext .ts,.tsx
ESLint couldn't find an eslint.config.(js|mjs|cjs) file.
```

Status: **NOT_CONFIGURED** (real finding — not fabricated, not silently skipped). Setting up an ESLint flat config
for this app was out of this pass's scope; recorded here honestly rather than invented as "passing."
