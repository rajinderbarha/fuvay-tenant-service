import { ROUTE_REGISTRY, type RouteId } from "../route-registry";
import type { ParsedDeepLink } from "./deep-link-parser";

export type DeepLinkRejectionReason =
  | "unknown_scheme_or_host"
  | "unknown_path"
  | "route_not_deep_link_eligible"
  | "malformed_param"
  | "unexpected_query_field"
  | "token_like_query_rejected"
  | "nested_redirect_rejected"
  | "expired_link"
  | "cross_marketplace_rejected";

export interface ValidatedDeepLink {
  routeId: RouteId;
  params: Record<string, string>;
  campaignCode?: string;
  referralCode?: string;
}

export type DeepLinkValidationResult = { ok: true; destination: ValidatedDeepLink } | { ok: false; reason: DeepLinkRejectionReason };

/** path template -> route id. Only routes explicitly marked `deepLinkEnabled` in the registry may appear here. */
const PATH_ROUTES: { pattern: RegExp; paramNames: string[]; routeId: RouteId }[] = [
  { pattern: /^$/, paramNames: [], routeId: "baselineLanding" },
  { pattern: /^home$/, paramNames: [], routeId: "home" },
  { pattern: /^search$/, paramNames: [], routeId: "search" },
  { pattern: /^categories\/([A-Za-z0-9_-]{1,64})$/, paramNames: ["categoryId"], routeId: "categoryDetail" },
  {
    pattern: /^categories\/([A-Za-z0-9_-]{1,64})\/services\/([A-Za-z0-9_-]{1,64})$/,
    paramNames: ["categoryId", "serviceId"],
    routeId: "serviceDetails",
  },
  { pattern: /^bookings$/, paramNames: [], routeId: "bookingsList" },
  { pattern: /^bookings\/([A-Za-z0-9_-]{1,64})$/, paramNames: ["bookingId"], routeId: "bookingDetail" },
  { pattern: /^rewards$/, paramNames: [], routeId: "rewards" },
  { pattern: /^support$/, paramNames: [], routeId: "support" },
  { pattern: /^legal\/terms$/, paramNames: [], routeId: "legalTerms" },
  { pattern: /^legal\/privacy$/, paramNames: [], routeId: "legalPrivacy" },
];

const ALLOWED_QUERY_KEYS = new Set(["campaign", "ref", "exp", "src"]);
const SENSITIVE_QUERY_KEY_PATTERN = /(token|otp|password|secret|session|auth|access_key|api_key)/i;
const REDIRECT_LIKE_VALUE_PATTERN = /https?:\/\//i;

export function validateDeepLink(
  link: ParsedDeepLink,
  opts: { nowIso?: string; marketplaceId?: string; linkMarketplaceId?: string } = {}
): DeepLinkValidationResult {
  if (link.source === "unknown") {
    return { ok: false, reason: "unknown_scheme_or_host" };
  }

  for (const key of Object.keys(link.query)) {
    if (SENSITIVE_QUERY_KEY_PATTERN.test(key)) {
      return { ok: false, reason: "token_like_query_rejected" };
    }
    if (!ALLOWED_QUERY_KEYS.has(key)) {
      return { ok: false, reason: "unexpected_query_field" };
    }
    if (REDIRECT_LIKE_VALUE_PATTERN.test(link.query[key])) {
      return { ok: false, reason: "nested_redirect_rejected" };
    }
  }

  if (opts.linkMarketplaceId && opts.marketplaceId && opts.linkMarketplaceId !== opts.marketplaceId) {
    return { ok: false, reason: "cross_marketplace_rejected" };
  }

  if (link.query.exp) {
    const now = opts.nowIso ? new Date(opts.nowIso).getTime() : Date.now();
    const expiresAtMs = Number(link.query.exp) * 1000;
    if (!Number.isFinite(expiresAtMs) || now >= expiresAtMs) {
      return { ok: false, reason: "expired_link" };
    }
  }

  const match = PATH_ROUTES.find((candidate) => candidate.pattern.test(link.path));
  if (!match) {
    return { ok: false, reason: "unknown_path" };
  }

  const definition = ROUTE_REGISTRY[match.routeId];
  if (!definition.deepLinkEnabled) {
    return { ok: false, reason: "route_not_deep_link_eligible" };
  }

  const execResult = match.pattern.exec(link.path);
  const params: Record<string, string> = {};
  match.paramNames.forEach((name, index) => {
    const value = execResult?.[index + 1];
    if (!value || !/^[A-Za-z0-9_-]{1,64}$/.test(value)) {
      params.__invalid = "true";
      return;
    }
    params[name] = value;
  });

  if (params.__invalid) {
    return { ok: false, reason: "malformed_param" };
  }

  return {
    ok: true,
    destination: { routeId: match.routeId, params, campaignCode: link.query.campaign, referralCode: link.query.ref },
  };
}
