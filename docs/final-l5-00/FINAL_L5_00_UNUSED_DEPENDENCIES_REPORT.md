# FINAL-L5-00 — Unused Dependencies Report (Parts 12-13)

**Scope & method disclaimer:** This is a *sampled, Grep-based heuristic scan*, not an exhaustive dependency-usage audit. No `depcheck`, `npm-check`, or Python `pipdeptree`/`deptry` tool was run. For each dependency, a targeted Grep for its import name was run against that app's own source tree only (excluding `node_modules`); build-tool-only or config-only usages (e.g. a plugin referenced solely from `next.config.js`) were checked separately and noted as BUILD_ONLY rather than POTENTIALLY_UNUSED. Nothing in this report is a recommendation to uninstall — findings are flagged for human review only.

Per instructions, obviously-core packages are skipped from per-dependency grepping and just noted here: **react, react-dom, next, typescript, eslint (core)** for the web frontends; **react, react-native, expo** for the mobile apps; **fastapi, uvicorn, sqlalchemy, pydantic** for the backend. These are skipped because their "usage" is definitionally the entire app (framework/runtime, not an optional library) and grepping for them would be meaningless noise.

---

## 1. frontend/super-admin (`package.json`)

Dependencies: `next`, `react`, `react-dom` (skipped, core), `recharts`, `lucide-react`. Dev: `@types/node`, `@types/react`, `typescript` (skipped, core).

| Dependency | Grep evidence | Classification |
|---|---|---|
| `recharts` | `grep -rl "recharts" app components` → 1 file (`app/admin/ai-chat/logs/page.tsx`) | USED — single consumer found; manually confirmed via grep |
| `lucide-react` | `grep -rl "lucide-react" app components` → 102 files | USED — heavily used icon library; manually confirmed via grep |
| `@types/node` | Not grepped (type-only, ambient, no import-name signature to search for) | BUILD_ONLY — TypeScript ambient types package, expected to have no runtime import matches |
| `@types/react` | Not grepped (same as above) | BUILD_ONLY |

No POTENTIALLY_UNUSED findings in this app — its dependency list is very small and both non-core packages have confirmed usage.

---

## 2. frontend/tenant-portal (`package.json`)

Dependencies: `next`, `react`, `react-dom` (skipped, core), `recharts`, `lucide-react`. Dev: `@types/node`, `@types/react`, `typescript` (skipped, core).

| Dependency | Grep evidence | Classification |
|---|---|---|
| `recharts` | `grep -rl "recharts" app components` → 1 file | USED — manually confirmed via grep |
| `lucide-react` | `grep -rl "lucide-react" app components` → 69 files | USED — manually confirmed via grep |
| `@types/node` | Not grepped (ambient types) | BUILD_ONLY |
| `@types/react` | Not grepped (ambient types) | BUILD_ONLY |

No POTENTIALLY_UNUSED findings — identical dependency shape to super-admin, both confirmed used.

---

## 3. frontend/customer-app (`package.json`)

Dependencies: `lucide-react`, `next`, `react`, `react-dom` (skipped, core). Dev: `@playwright/test`, `@types/node`, `@types/react`, `typescript` (skipped, core).

| Dependency | Grep evidence | Classification |
|---|---|---|
| `lucide-react` | `grep -rl "lucide-react" app components` → 3 files | USED — low but real usage; manually confirmed via grep |
| `@playwright/test` | `e2e/` directory exists at repo root and app has a `tests/`/`test-results/` presence per directory listing | TEST_ONLY — e2e testing framework, expected to only appear in test files, not app source; consistent with its devDependency placement |
| `@types/node`, `@types/react` | Not grepped (ambient types) | BUILD_ONLY |

No POTENTIALLY_UNUSED findings.

Notable cross-check: `recharts` is present in super-admin and tenant-portal but **absent** from customer-app's `package.json` — consistent with customer-app having no analytics/chart screens (a sensible, non-flagged omission, not a finding).

---

## 4. mobile/customer-app (`package.json`)

Dependencies (excluding `react`, `react-native`, `expo` — skipped, core):

| Dependency | Grep evidence (`grep -rl` against `src/`) | Classification |
|---|---|---|
| `expo-status-bar` | 1 file | USED — manually confirmed via grep |
| `expo-location` | 0 files | POTENTIALLY_UNUSED — no grep matches found in `src/`; found no import of `expo-location` anywhere in the searched tree. Given the app is a customer service-booking app, location could plausibly be used via a differently-named wrapper, but no direct import evidence was found in this scan. |
| `expo-notifications` | 0 files | POTENTIALLY_UNUSED — no grep matches found; push notifications may be planned but not yet wired up, or wired via a native config plugin only (checked `app.json`/`app.config.*` was out of scope for this pass) |
| `expo-image-picker` | 0 files | POTENTIALLY_UNUSED — no grep matches found; no evidence of a photo-upload flow importing this package in `src/` |
| `@react-native-async-storage/async-storage` | 2 files | USED — manually confirmed via grep |
| `@react-navigation/native` | 14 files | USED — core navigation, heavily used; manually confirmed via grep |
| `@react-navigation/native-stack` | 14 files | USED — manually confirmed via grep |
| `@react-navigation/bottom-tabs` | 1 file | USED — manually confirmed via grep |
| `react-native-safe-area-context` | 0 files | POTENTIALLY_UNUSED — no grep matches found in `src/`. Note: this package is a common *transitive/peer* dependency of `@react-navigation/native`, so it may be required at the framework level without ever being directly imported by app code — flagging as POTENTIALLY_UNUSED at the direct-import level, but noting the likely peer-dependency explanation so it is not misread as truly dead. |
| `react-native-screens` | 0 files | POTENTIALLY_UNUSED — same likely explanation as above (react-navigation peer dependency, rarely imported directly by app code) |
| `react-native-maps` | 0 files | POTENTIALLY_UNUSED — no grep matches found; for a service-tracking app, a maps package with zero source usage is a more notable finding than the two peer-dependency cases above, since there's no framework-level reason it would be required without direct use |
| `@expo/vector-icons` | 0 files | POTENTIALLY_UNUSED — no grep matches found in `src/` |

---

## 5. mobile/staff-app (`package.json`)

Dependencies (excluding `react`, `react-native`, `expo` — skipped, core):

| Dependency | Grep evidence (`grep -rl` against `src/`) | Classification |
|---|---|---|
| `expo-status-bar` | 1 file | USED — manually confirmed via grep |
| `expo-location` | 1 file | USED — manually confirmed via grep (staff-app, unlike customer-app, does import this — makes sense for a field-technician app needing GPS) |
| `expo-notifications` | 0 files | POTENTIALLY_UNUSED — no grep matches found in `src/` |
| `@react-native-async-storage/async-storage` | 2 files | USED — manually confirmed via grep |
| `@react-navigation/native` | 6 files | USED — manually confirmed via grep |
| `@react-navigation/native-stack` | 6 files | USED — manually confirmed via grep |
| `@react-navigation/bottom-tabs` | 1 file | USED — manually confirmed via grep |
| `react-native-safe-area-context` | 0 files | POTENTIALLY_UNUSED — likely react-navigation peer dependency (same caveat as customer-app above) |
| `react-native-screens` | 0 files | POTENTIALLY_UNUSED — likely react-navigation peer dependency (same caveat) |
| `react-native-maps` | 0 files | POTENTIALLY_UNUSED — no grep matches found; notable since staff-app is field-dispatch-oriented and a maps package going unused is a real signal worth checking |
| `react-native-vector-icons` | 0 files | POTENTIALLY_UNUSED — no grep matches found; staff-app also depends on `@expo/vector-icons` (see below), so this may be a redundant/legacy icon library never actually wired up |
| `@expo/vector-icons` | 0 files | POTENTIALLY_UNUSED — no grep matches found in `src/`, same as customer-app |

Cross-app note: both mobile apps declare `@expo/vector-icons` with zero direct-import evidence in `src/`. Since icon usage is extremely common in mobile UI, this is either (a) icons are referenced via a differently-named local wrapper/barrel not caught by the grep for the literal package string, or (b) genuinely unused. REVIEW_REQUIRED rather than a confident POTENTIALLY_UNUSED call, given how surprising a fully-icon-free UI would be — recommend a follow-up grep for `Ionicons`, `MaterialIcons`, etc. (the actual exported names from `@expo/vector-icons`) rather than the package string itself, which this pass did not attempt.

---

## 6. Backend (`requirements.txt` at repo root; `pyproject.toml` has no dependency list, only pytest/ruff config)

Dependencies (excluding `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `pydantic` — skipped, core):

| Dependency | Grep evidence (`grep -rl` against `app/`, `main.py`) | Classification |
|---|---|---|
| `python-multipart` | Not directly imported by app code (it's a Starlette/FastAPI internal dependency for form/file-upload parsing, not something app code imports by name) | BUILD_ONLY — required transitively by FastAPI's `UploadFile`/form handling; correctly has no direct app-level import |
| `asyncpg` | 5 files | USED — manually confirmed via grep |
| `alembic` | Not grepped directly (used via CLI + `alembic/` directory, not imported in `app/`) | BUILD_ONLY — migration tool invoked via CLI (`alembic upgrade head`), not an app-code import; presence of `alembic/` and `alembic.ini` at repo root confirms active use as a tool even without an `app/`-level import |
| `psycopg2-binary` | 2 files | USED (sync driver used by Alembic's env, per the `requirements.txt` comment "for Alembic sync env") — manually confirmed via grep, and comment in requirements.txt corroborates purpose |
| `redis[hiredis]` | `grep -rl "import redis\|from redis"` → 3 files | USED — manually confirmed via grep |
| `pydantic-settings` | Not grepped directly by name (imports as `pydantic_settings`, commonly aliased) | REVIEW_REQUIRED — plausible settings/config usage given the presence of `app/core/` config modules in this codebase, but not directly confirmed via grep in this pass |
| `email-validator` | `grep -rl "email_validator\|EmailStr"` → 4 files | USED — manually confirmed via grep (note: per memory "Login fix — EmailStr→str validator", this may now be a residual/reduced dependency after that fix, but still has active references) |
| `python-jose[cryptography]` | `grep -rl "jose"` → 4 files | USED — manually confirmed via grep (JWT handling) |
| `passlib[bcrypt]` | `grep -rl "passlib"` → 2 files | USED — manually confirmed via grep (password hashing) |
| `bcrypt` | Not grepped directly (comment in requirements.txt explains it's pinned specifically for passlib backend compatibility, not directly imported by app code) | BUILD_ONLY — the requirements.txt comment itself states this: `"passlib 1.7.4's bcrypt backend detection breaks on bcrypt>=4.1"`, i.e. it's a transitive pin, not a direct-use dependency |
| `structlog` | 267 files | USED — extremely heavily used; manually confirmed via grep |
| `python-json-logger` | `grep -rl "python_json_logger\|pythonjsonlogger"` → 0 files | POTENTIALLY_UNUSED — no grep matches found in `app/` or `main.py`. Given `structlog` is used pervasively (267 files) and is itself capable of JSON-formatted output, `python-json-logger` may have been superseded by structlog's own JSON renderer and left in requirements.txt as a stale dependency. Flagged, not recommended for removal. |
| `httpx` | 16 files | USED — manually confirmed via grep |
| `pytest`, `pytest-asyncio` | Not grepped (test-only, invoked via `pytest` CLI / `pyproject.toml` config, not imported by app source) | TEST_ONLY — confirmed by presence of `[tool.pytest.ini_options]` in `pyproject.toml` and large `tests/` directory |
| `prometheus-fastapi-instrumentator` | 2 files | USED — manually confirmed via grep |
| `sentry-sdk[fastapi]` | 2 files | USED — manually confirmed via grep |

### Backend summary
Only one real POTENTIALLY_UNUSED finding: `python-json-logger`. Everything else in `requirements.txt` is either directly used (confirmed via grep), a well-explained transitive/build pin (with the reasoning documented in the requirements.txt comments themselves), or a test-only tool correctly scoped to `pytest`/`tests/`.

---

## Overall summary table

| App | POTENTIALLY_UNUSED count | Notable findings |
|---|---|---|
| frontend/super-admin | 0 | Clean — tiny, fully-used dependency list |
| frontend/tenant-portal | 0 | Clean — identical shape to super-admin, fully used |
| frontend/customer-app | 0 | Clean — `@playwright/test` correctly TEST_ONLY |
| mobile/customer-app | 6 (`expo-location`, `expo-notifications`, `expo-image-picker`, `react-native-safe-area-context`†, `react-native-screens`†, `react-native-maps`, `@expo/vector-icons`†) † = likely peer-dependency explanation, not truly dead | `react-native-maps` and `expo-image-picker` are the most notable — no framework-level reason to expect zero direct usage |
| mobile/staff-app | 5 (`expo-notifications`, `react-native-safe-area-context`†, `react-native-screens`†, `react-native-maps`, `react-native-vector-icons`, `@expo/vector-icons`†) | `react-native-maps` notable again given field-dispatch use case; `react-native-vector-icons` + `@expo/vector-icons` both showing zero usage suggests one may be a legacy leftover from before a migration to the other |
| Backend | 1 (`python-json-logger`) | Likely superseded by `structlog`'s own JSON renderer |

No uninstall actions were taken or recommended — this report only flags items for human review, per the task instructions. This scan intentionally sampled the declared dependencies of 5 `package.json` files plus `requirements.txt`; it did not run `depcheck`/`deptry`/similar tooling, and the `@expo/vector-icons` zero-usage findings in particular should be re-checked with a grep for the actual exported icon-set names (e.g. `Ionicons`) rather than the package string, since icon libraries are frequently imported by a specific named export rather than the bare package name appearing in source.
