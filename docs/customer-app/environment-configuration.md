# Customer App — Environment Configuration

## Files

- `.env.example` — documented template, no real credentials.
- `.env` / `.env.local` (gitignored) — actual local values, copied from the
  example.
- `src/config/environment.ts` — the only file allowed to read
  `process.env.EXPO_PUBLIC_*` directly. Everything else imports
  `environment` from here.
- `src/config/app-config.ts` — non-secret, non-environment-varying app
  defaults (locale list, pagination defaults, touch target size, ...).

## Variables

| Variable | Purpose | Required in prod/staging |
|---|---|---|
| `EXPO_PUBLIC_APP_ENV` | `local\|development\|test\|staging\|production` | recommended |
| `EXPO_PUBLIC_API_URL` | Backend base URL | **yes** — build fails without it |
| `EXPO_PUBLIC_API_TIMEOUT_MS` | Request timeout | no (defaults to 15000) |
| `EXPO_PUBLIC_BUILD_VERSION` / `EXPO_PUBLIC_BUILD_NUMBER` | Safe-to-display build metadata | no |
| `EXPO_PUBLIC_ANALYTICS_ENABLED` | Enables the analytics adapter | no |
| `EXPO_PUBLIC_CRASH_REPORTING_ENABLED` | Enables the crash-reporting adapter | no |
| `EXPO_PUBLIC_LOG_LEVEL` | `debug\|info\|warn\|error` | no |
| `EXPO_PUBLIC_MOCK_MODE` | Enables mock mode | **must be false/unset** — build fails if true in production |
| `EXPO_PUBLIC_DEEP_LINK_SCHEME` | URL scheme for deep links | no |

There is no separate backend-secrets file in this app — Expo's
`EXPO_PUBLIC_*` prefix convention means anything under that prefix ships in
the client bundle. Nothing secret (API keys, signing secrets) may ever be
given an `EXPO_PUBLIC_*` name. The DeepSeek key, for example, deliberately
stays backend-only and is never referenced here.

## Validation Behavior

`environment.ts` builds its config once at module load:

- **local / development / test**: missing `EXPO_PUBLIC_API_URL` falls back
  to `http://localhost:8000` so a fresh clone still boots with `expo
  start`.
- **staging / production**: the same gaps (missing API URL, `localhost` API
  URL, or `EXPO_PUBLIC_MOCK_MODE=true`) throw an `EnvironmentValidationError`
  at startup instead of silently shipping a broken/insecure build.

## Adding a New Variable

1. Add it to `.env.example` with a comment.
2. Add a typed field to the `Environment` interface and `buildEnvironment()`
   in `environment.ts`.
3. If it's required for staging/production correctness, add it to the
   `issues` validation list.
4. Never read it via `process.env` anywhere else in the codebase.
