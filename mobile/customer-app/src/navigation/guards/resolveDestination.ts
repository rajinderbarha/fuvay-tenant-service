import { AppNavigationSnapshot, RootDestination } from "./types";

/**
 * Pure, deterministic route resolver (spec section 10-11). Takes a full
 * snapshot, returns exactly one destination. No side effects, no React,
 * no direct store reads -- this is what makes guard precedence testable
 * without mounting a single component.
 *
 * Precedence (fail-closed, highest first -- a lower-priority state must
 * NEVER override a higher one):
 *   1. Storage unavailable/corrupted
 *   2. Forced update (unsupported/update_required)
 *   3. Platform maintenance
 *   4. API unavailable during mandatory bootstrap
 *   5. Account suspended/rejected/disabled
 *   6. Session expired
 *   7. Invalid audience (non-customer token reached this app)
 *   8. Unauthenticated
 *   9. Bootstrap still in progress
 *  10. Selected/pending-deep-link vertical disabled
 *  11. Authenticated customer shell (+ authorized pending deep link)
 */
export function resolveDestination(snapshot: AppNavigationSnapshot): RootDestination {
  if (snapshot.storage === "unavailable" || snapshot.storage === "corrupted") {
    return { tree: "ExceptionalStateStack", screen: "StorageUnavailable", reason: snapshot.storage };
  }

  if (snapshot.appVersion === "update_required" || snapshot.appVersion === "unsupported") {
    return { tree: "ExceptionalStateStack", screen: "UpdateRequired", reason: snapshot.appVersion };
  }

  if (snapshot.platform === "maintenance") {
    return { tree: "ExceptionalStateStack", screen: "Maintenance", reason: "maintenance" };
  }

  if (snapshot.platform === "api_unavailable" && snapshot.bootstrap !== "ready") {
    // Only treated as a hard bootstrap blocker while bootstrap is still
    // mandatory (i.e. before a customer shell has ever been reached this
    // session) -- see offline-behavior distinction in spec section 14;
    // once ready, a previously-authenticated shell may render with an
    // offline banner instead (that decision lives in the shell, not here).
    return { tree: "ExceptionalStateStack", screen: "ApiUnavailable", reason: "api_unavailable" };
  }

  if (snapshot.account === "suspended" || snapshot.account === "rejected" || snapshot.account === "disabled") {
    return { tree: "ExceptionalStateStack", screen: "AccountSuspended", reason: snapshot.account };
  }

  if (snapshot.auth === "session_expired") {
    return { tree: "ExceptionalStateStack", screen: "SessionExpired", reason: "session_expired" };
  }

  if (snapshot.auth === "invalid_audience") {
    return { tree: "ExceptionalStateStack", screen: "InvalidAccess", reason: "invalid_audience" };
  }

  if (snapshot.auth === "unauthenticated" || snapshot.auth === "unknown") {
    return { tree: "PublicStack", screen: "Welcome" };
  }

  if (snapshot.bootstrap !== "ready") {
    return { tree: "Bootstrap" };
  }

  // snapshot.auth === "authenticated_customer" from here on.
  const pending = snapshot.pendingDeepLink;
  if (pending && pending.validated) {
    const targetVertical = pending.params.vertical;
    if (targetVertical && !snapshot.enabledVerticals.enabled.includes(targetVertical as never)) {
      return { tree: "ExceptionalStateStack", screen: "VerticalUnavailable", reason: "vertical_disabled" };
    }
    return { tree: "CustomerAppStack", pendingDeepLink: pending };
  }
  if (pending && !pending.validated) {
    // A rejected/malformed link must never crash or silently redirect
    // somewhere unexpected -- fall through to the plain authenticated
    // shell, exactly as if no deep link had been present.
    return { tree: "CustomerAppStack" };
  }

  return { tree: "CustomerAppStack" };
}

/** A short, stable string identifying which top-level tree+screen a
 * destination targets -- used to decide whether the navigator needs a
 * hard reset (see navigation/navigationReset.ts) without deep-comparing
 * the whole object on every render. */
export function destinationSignature(destination: RootDestination): string {
  if (destination.tree === "ExceptionalStateStack") return `${destination.tree}:${destination.screen}`;
  if (destination.tree === "PublicStack") return `${destination.tree}:${destination.screen}`;
  return destination.tree;
}
