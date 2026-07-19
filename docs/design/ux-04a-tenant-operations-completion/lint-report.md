# Lint Report

**NOT_CONFIGURED — genuinely, not fabricated around.**

`frontend/tenant-portal/package.json`'s `lint` script is `next lint`.
Running it under the installed Next.js 16.2.9:

```
npm run lint
> next lint
Invalid project directory provided, no such directory: /root/.../lint
```

`npx next --help` confirms `next lint` is no longer a recognized
subcommand in Next.js 16 — it was removed upstream (Next.js 16 dropped the
built-in `next lint` command in favor of external tooling such as a
standalone ESLint config, which this workspace does not have configured).
This is a pre-existing condition, not something this pass broke — no
lint tooling was ever actually runnable for `frontend/tenant-portal` on
this Next.js version. No lint config was invented to force a "pass."
Same result for `frontend/super-admin` (same Next.js version, same `next
lint` script).
