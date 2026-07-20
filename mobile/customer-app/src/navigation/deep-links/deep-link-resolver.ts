import { parseDeepLink } from "./deep-link-parser";
import { validateDeepLink, type DeepLinkRejectionReason } from "./deep-link-validator";
import { setPendingDestination } from "./pending-deep-link-store";
import { evaluateRouteAccess, type RouteGuardContext } from "../route-guards";
import { getRouteDefinition, type RouteId } from "../route-registry";
import { logger } from "../../observability/logger";

export type DeepLinkResolution =
  | { outcome: "rejected"; reason: DeepLinkRejectionReason | "parse_failed" }
  | { outcome: "deferred"; routeId: RouteId }
  | { outcome: "ready"; routeId: RouteId; params: Record<string, string> };

/**
 * Full pipeline: parse -> security-validate -> evaluate against current
 * route guards. A destination that requires authentication or a maintenance
 * gate is deferred into the pending-destination store rather than navigated
 * to directly — mandatory system gates always win (see route-guards.ts).
 */
export function resolveDeepLink(rawUrl: string, guardContext: RouteGuardContext, opts: { marketplaceId?: string; nowIso?: string } = {}): DeepLinkResolution {
  const parsed = parseDeepLink(rawUrl);
  if (!parsed.ok) {
    logger.info("deep_link.rejected", { reason: parsed.reason });
    return { outcome: "rejected", reason: "parse_failed" };
  }

  const validation = validateDeepLink(parsed.link, { nowIso: opts.nowIso, marketplaceId: opts.marketplaceId });
  if (!validation.ok) {
    logger.info("deep_link.rejected", { reason: validation.reason });
    return { outcome: "rejected", reason: validation.reason };
  }

  const { routeId, params } = validation.destination;
  const guardResult = evaluateRouteAccess(routeId, { ...guardContext, viaDeepLink: true });

  if (guardResult.decision === "allow") {
    logger.info("deep_link.opened", { routeId });
    return { outcome: "ready", routeId, params };
  }

  if (guardResult.decision === "deny-auth" || guardResult.decision === "deny-not-ready") {
    const definition = getRouteDefinition(routeId);
    setPendingDestination({
      routeId,
      params,
      source: "custom-scheme",
      requiresAuth: guardResult.decision === "deny-auth",
      requiresMarketplace: definition?.access === "marketplace-required",
    });
    logger.info("deep_link.deferred", { routeId, decision: guardResult.decision });
    return { outcome: "deferred", routeId };
  }

  logger.info("deep_link.rejected", { reason: guardResult.decision });
  return { outcome: "rejected", reason: "route_not_deep_link_eligible" };
}
