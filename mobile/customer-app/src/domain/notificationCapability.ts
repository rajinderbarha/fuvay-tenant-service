/**
 * Truthful push-notification capability for the booking receipt (spec
 * section 7). `expo-notifications` is listed in `package.json`/`app.json`
 * plugins (Notification Center phase audit, corrected from an earlier,
 * inaccurate claim that no such dependency existed) but is never imported
 * anywhere in `src/` -- there is no permission-request call, no device-token
 * registration, and no push-received handler wired up. The dependency's
 * presence is not a capability by itself. Rather than fabricate an "On"
 * state, this module has exactly one honest value until that infrastructure
 * is actually built.
 */
export type NotificationCapability =
  | { kind: "enabled" }
  | { kind: "permission_not_granted" }
  | { kind: "unavailable" };

/** No push transport is wired into this app yet -- always `unavailable`.
 * Kept as a function (not a constant) so the day real push infrastructure
 * lands, only this one call site needs to change. */
export function resolveNotificationCapability(): NotificationCapability {
  return { kind: "unavailable" };
}
