import { PendingDeepLink, PendingDeepLinkRejectReason, EnabledVerticalSummary } from "./types";
import { CustomerAudience } from "../../domain/auth";
import { VerticalKey } from "../../domain/catalog";

/**
 * Typed deep-link allowlist (spec section 16). Route CONTRACTS only --
 * none of these have a real product screen yet, so every entry resolves
 * to a safe placeholder/Home shell today, never an invented feature
 * screen. Backend ownership validation (does this booking/job/quote
 * belong to the calling customer) is explicitly deferred to Phase F's
 * API layer -- this allowlist only validates shape, auth requirement and
 * vertical availability, which is everything decidable client-side.
 */
export interface DeepLinkRouteSpec {
  routeKey: string;
  requiresAuth: boolean;
  vertical: VerticalKey | "global";
  /** Required param names -- presence only; format is spec'd per-route
   * where it matters (currently all are opaque ID strings). */
  requiredParams: readonly string[];
}

export const DEEP_LINK_ALLOWLIST: Record<string, DeepLinkRouteSpec> = {
  "booking.detail": { routeKey: "booking.detail", requiresAuth: true, vertical: "home_services", requiredParams: ["bookingId"] },
  "serviceJob.tracking": { routeKey: "serviceJob.tracking", requiresAuth: true, vertical: "home_services", requiredParams: ["jobId"] },
  "quote.review": { routeKey: "quote.review", requiresAuth: true, vertical: "home_services", requiredParams: ["quoteId"] },
  "conversation.detail": { routeKey: "conversation.detail", requiresAuth: true, vertical: "global", requiredParams: ["conversationId"] },
  "notification.destination": { routeKey: "notification.destination", requiresAuth: true, vertical: "global", requiredParams: ["notificationId"] },
  "support.case": { routeKey: "support.case", requiresAuth: true, vertical: "global", requiredParams: ["complaintId"] },
  "profile.destination": { routeKey: "profile.destination", requiresAuth: true, vertical: "global", requiredParams: [] },
  "vertical.selected": { routeKey: "vertical.selected", requiresAuth: true, vertical: "global", requiredParams: ["vertical"] },
};

/** Route-name prefixes that must NEVER be reachable from this app, even if
 * a malicious/malformed push payload names them explicitly. */
const FORBIDDEN_ROUTE_PREFIXES = ["staff.", "tenant.", "admin.", "provider.", "technician."];

export interface ValidateDeepLinkInput {
  routeKey: string;
  params: Record<string, string>;
  isAuthenticated: boolean;
  audience: CustomerAudience | string | null;
  enabledVerticals: EnabledVerticalSummary;
}

/**
 * Validates an untrusted deep-link payload (from a notification, a
 * universal link, anything not already trusted app state) against the
 * allowlist. Never navigates directly from the raw string -- this always
 * returns a `PendingDeepLink` for the resolver to consume, and a rejected
 * link is inert rather than thrown (a malformed link must not crash the
 * app -- spec section 11/16).
 */
export function validateDeepLink(input: ValidateDeepLinkInput): PendingDeepLink {
  const reject = (reason: PendingDeepLinkRejectReason): PendingDeepLink => ({
    routeKey: input.routeKey,
    params: input.params,
    validated: false,
    rejectedReason: reason,
  });

  if (FORBIDDEN_ROUTE_PREFIXES.some(prefix => input.routeKey.startsWith(prefix))) {
    return reject("unknown_route");
  }

  const spec = DEEP_LINK_ALLOWLIST[input.routeKey];
  if (!spec) {
    return reject("unknown_route");
  }

  for (const requiredParam of spec.requiredParams) {
    const value = input.params[requiredParam];
    if (!value || typeof value !== "string" || value.trim() === "") {
      return reject("malformed_params");
    }
  }

  if (spec.requiresAuth && !input.isAuthenticated) {
    return reject("requires_auth");
  }

  if (spec.requiresAuth && input.audience !== "serviceos:customer") {
    return reject("wrong_audience");
  }

  if (spec.vertical !== "global" && !input.enabledVerticals.enabled.includes(spec.vertical)) {
    return reject("vertical_disabled");
  }

  return { routeKey: input.routeKey, params: input.params, validated: true };
}
