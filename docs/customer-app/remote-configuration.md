# Customer App — Remote Configuration

## 1. Schema

`src/remote-config/remote-config-schema.ts` (Zod) defines the versioned
envelope: `schemaVersion` (currently `1`, a `z.literal`), `configVersion`,
`generatedAt`/`expiresAt`, `environment`, `marketplace`, `application`,
`versionPolicy`, `maintenance`, `modules[]`, `navigation`. Cross-field rules
(`superRefine`) reject: `expiresAt` before `generatedAt`, duplicate module
keys, a module depending on an unknown module, a cyclic module dependency
graph, `enabled maintenance` with `type: "none"`, `estimatedEndAt` before
`startAt`, a `fallbackRouteId`/`initialRouteOverride` not present in a
non-empty `allowedRouteIds`, and an enabled module whose route is in
`disabledRouteIds`. Only `https://` store/status-page URLs are accepted.

## 2. Trust Model

**Honest gap**: the backend does not currently issue cryptographically
signed configuration. `config-integrity.ts#verifyConfigIntegrity` therefore
never returns `"trusted"` — it validates three things and returns
`"unverified"` at best: the config's declared `environment` matches the
build's environment (via `bindableEnvironmentName`, which treats
`local`/`test` client builds as `development` for this comparison since the
backend has no such environments), the config's `marketplace.marketplaceId`
matches the requesting context, and — for staging/production — the config
was served from a compiled allowlist of trusted hosts
(`TRUSTED_HOSTS_BY_ENV`). Any mismatch returns `"rejected"`, and a rejected
config is never used (`remote-config-service.ts` throws `integrity_failure`
and falls back to cache/defaults). Adding real signature verification is a
backend + mobile joint effort tracked in `known-gaps.md`.

## 3. Fetch Lifecycle

`remote-config-client.ts#fetchRemoteConfig`: sends `If-None-Match` when a
cached ETag exists, treats HTTP 304 as `"not-modified"`, validates
`content-type: application/json`, enforces a 256KB response-size guard
(both via `content-length` header and actual body length), parses JSON
defensively (catches `JSON.parse` throwing), checks `schemaVersion` before
full Zod parsing (fast-fails an incompatible version with a distinct error
category), then runs the full schema. Never retries a schema/integrity
failure automatically — only `server_error`/`timeout`/`network_error` are
marked `retryable`.

## 4. Cache Lifecycle

`remote-config-cache.ts`: stored via `preferenceStorage` (non-sensitive —
the schema has no secret fields) under
`PREFERENCE_STORAGE_KEYS.remoteConfigCache`. On read, the embedded payload
is re-validated against the Zod schema (not trusted just because it was
previously written) — a corrupted or partially-written entry is treated as
absent. `evaluateCacheUsability` rejects on `environment_mismatch`,
`marketplace_mismatch`, `expired` (past `expiresAt`), or `too_old` (past
`application.maxConfigAgeSeconds`), and only permits an expired/too-old
entry through when `application.cachedConfigFallbackAllowed` is true.

## 5. Source Priority

`ConfigSource` (`compiled-defaults | cache-fresh | cache-stale-permitted |
remote-fresh | remote-not-modified`) is recorded on every resolved config
and surfaced in `StartupSnapshot.resolvedConfig.source` and the dev
inspector. Resolution order in `startup-service.ts`: load cache (if usable)
→ attempt remote fetch (skipped entirely when offline) → on fetch success,
replace with `remote-fresh`/`remote-not-modified` → on fetch failure, keep
whatever cache/defaults were already loaded.

## 6. Expiry / Versioning / Environment / Marketplace Binding

Expiry (`expiresAt`) and max-age (`maxConfigAgeSeconds`) are both enforced
independently (see §4). Environment and marketplace binding are enforced
twice — once by `config-integrity.ts` at fetch time, once by
`remote-config-cache.ts` at cache-read time — so a config fetched under one
environment/marketplace can never silently apply to another, even if the
two checks drift.

## 7. Feature Evaluation

`remote-config-evaluator.ts#evaluateModule` is the single fail-closed
evaluator: `configuration-invalid` (unknown key) → `maintenance-disabled`
(blocking maintenance short-circuits everything) → `disabled` → `hidden` →
`unsupported-version` → `outside-region` → `dependency-disabled`
(recursive, safe because the schema already rejects cyclic graphs) →
`enabled`. `route-guards.ts` calls this for any route with
`access: "module-enabled"`.

## 8. Change Application

Not yet implemented as a live "config changed while app is running" push
mechanism — no server invalidation signal exists yet (explicitly deferred
by CUSTOMER-L5-01 §17 to "a future sprint"). This sprint's refresh triggers
are: cold start, explicit retry, and app resume after the 60-second minimum
interval (see `startup-architecture.md` §10). A change is applied by
re-running the whole startup flow and re-deriving `InitialRouteDecision` —
there is no in-place "patch this one section" mechanism yet.

## 9. Failure Behavior

See `startup-failure-matrix.md`.
