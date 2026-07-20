# Customer App — Startup Failure Matrix

| Failure | Detection point | Customer screen | Retry behavior | Fallback | Log level | Severity |
|---|---|---|---|---|---|---|
| Invalid production environment (missing/localhost API URL, mock mode on) | `config/environment.ts` throws at module load | App cannot boot at all (crash before React renders) | N/A — this is a build-config error, not a runtime one | None | fatal (thrown, caught by build tooling) | P0 (must never ship) |
| Unsupported/corrupted build (invalid remote schema version) | `remote-config-client.ts` schema-version pre-check | `unsupportedBuild` | No automatic retry (non-retryable category) | Falls back to cache/compiled-defaults for config, but route resolver still routes to `unsupportedBuild` if `buildSupported` is false | warn | P1 |
| Mandatory maintenance active | `maintenance-policy.ts#evaluateMaintenancePolicy` | `maintenance` | Retry button (if `retryAllowed`) re-runs startup | N/A | info | P1 (expected operational state) |
| Mandatory version update / blocked build | `version-policy.ts#evaluateVersionPolicy` | `mandatoryUpdate` | "Retry configuration" re-runs startup after store visit | N/A | info | P1 (expected operational state) |
| Marketplace/app disabled | `startup-route-resolver.ts` reads `marketplace.active`/`customerAppEnabled` | `appUnavailable` | None (policy state, not transient) | N/A | info | P1 |
| Remote config fetch: network error | `remote-config-client.ts` `fetch()` throws `TypeError` | Falls through to cache/defaults; if none, `offlineStartup` or `startupError` | Retryable — `remote-config-service.ts` re-attempted on explicit retry | Cache → compiled defaults | warn | P2 (transient) |
| Remote config fetch: timeout | `withTimeout` wrapper in `startup-service.ts` | Same as above | Retryable | Cache → compiled defaults | warn | P2 |
| Remote config fetch: invalid schema | `remote-config-client.ts` Zod `safeParse` fails | Same as above (fetch treated as failed) | **Not** automatically retried (malformed response cannot succeed on retry without a server-side fix) | Cache → compiled defaults | warn | P1 (indicates a backend contract break) |
| Remote config integrity rejection (env/marketplace/origin mismatch) | `config-integrity.ts#verifyConfigIntegrity` | Same as above | Not automatically retried | Cache → compiled defaults | warn | P0 (security-relevant — should never happen against the real backend) |
| Cache corrupted / wrong environment / wrong marketplace | `remote-config-cache.ts` re-validates on every read | Treated as "no cache" — falls through to fetch or defaults | N/A (self-healing on next successful fetch) | Compiled defaults | info | P3 |
| Offline, no usable cache | `startup-route-resolver.ts` (`connectivity === "offline" && configSource === "none"`) | `offlineStartup` | Retry button + "Open network settings" | N/A | info | P2 (expected) |
| Deep link: parse/validation failure | `deep-link-resolver.ts` | No screen change — silently ignored, default landing route used instead | N/A | Falls through to default landing | info | P3 |
| Deep link: requires auth, customer is guest | `deep-link-resolver.ts` → `pending-deep-link-store.ts` | `authentication` (once implemented in L5-02) | Deferred destination replays automatically after real login | N/A | info | P3 (expected) |
| Notification intent: unknown/expired/duplicate | `notification-intent.ts#resolveNotificationIntent` | No navigation occurs | N/A | Silently rejected, safely logged | info | P3 |
| Total startup timeout budget exceeded | Documented (12s) but **not separately enforced as a second timer** — see known-gaps.md | N/A — individual phase timeouts (8s remote-config fetch, etc.) are what actually fire | N/A | N/A | — | P2 (gap, not a false claim — no code claims to enforce this) |
| Unhandled exception anywhere in the startup pipeline | `startup-service.ts`'s outer `try/catch` | `startupError` | Retry button | N/A | error | P1 |

Every row's customer-facing text is localized (en/hi/pa) and contains no
raw error message, stack trace, or backend payload — only a safe title,
message, and (for `startupError`) a generated `errorReferenceId` a support
agent can correlate against logs.
