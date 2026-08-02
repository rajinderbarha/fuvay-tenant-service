import { RouteKey } from "./routeRegistry";

/**
 * Centralized, allow-listed deep-link parsing (spec section 8). Deep links
 * are handled manually (not via React Navigation's declarative `linking`
 * path-matching) because every link must pass through the same async guard
 * chain as a normal navigation -- a valid-looking URL is never enough on
 * its own (see guards/validateJobRoute.ts).
 *
 * The HTTPS universal-link domain is read from environment configuration,
 * never hardcoded -- until EXPO_PUBLIC_UNIVERSAL_LINK_HOST is set for a
 * real deployment, HTTPS links are simply not matched (custom-scheme links
 * still work for internal/dev use).
 */
const CUSTOM_SCHEME = "serviceos";
const UNIVERSAL_LINK_HOST = process.env.EXPO_PUBLIC_UNIVERSAL_LINK_HOST ?? "";

export interface ParsedDeepLink {
  routeKey: RouteKey;
  jobId?: string;
}

const JOB_SUBROUTE: Record<string, RouteKey> = {
  "": "JOB_DETAIL",
  inspection: "JOB_INSPECTION",
  estimate: "JOB_ESTIMATE",
  parts: "JOB_PARTS",
  checklist: "JOB_CHECKLIST",
  completion: "JOB_COMPLETION",
};

const TOP_LEVEL_ROUTE: Record<string, RouteKey> = {
  home: "HOME",
  jobs: "JOBS",
  schedule: "SCHEDULE",
  notifications: "NOTIFICATIONS",
  profile: "PROFILE",
};

function parsePath(pathSegments: string[]): ParsedDeepLink | null {
  const [first, second, third] = pathSegments;
  if (!first) return null;

  if (first === "jobs" && second) {
    const sub = third ?? "";
    const routeKey = JOB_SUBROUTE[sub];
    if (!routeKey) return null;
    return { routeKey, jobId: second };
  }

  const routeKey = TOP_LEVEL_ROUTE[first];
  if (!routeKey) return null;
  return { routeKey };
}

/**
 * Parses `serviceos://...` and (if configured) `https://<universal host>/...`
 * URLs into an allow-listed {routeKey, jobId} pair. Anything else --
 * unknown scheme, unknown host, unknown path, malformed input -- returns
 * null and the caller must fail closed (never fall back to opening an
 * external/arbitrary URL as an internal route).
 */
export function parseDeepLink(url: string): ParsedDeepLink | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  const segments = parsed.pathname.split("/").filter(Boolean);

  if (parsed.protocol === `${CUSTOM_SCHEME}:`) {
    // serviceos://jobs/123/inspection -> host="jobs", pathname="/123/inspection"
    const host = parsed.hostname || parsed.host;
    return parsePath([host, ...segments].filter(Boolean));
  }

  if (parsed.protocol === "https:" && UNIVERSAL_LINK_HOST && parsed.hostname === UNIVERSAL_LINK_HOST) {
    return parsePath(segments);
  }

  return null;
}

let pendingDeepLink: ParsedDeepLink | null = null;

/** Stored only while unauthenticated; the destination is revalidated (not
 * blindly replayed) after a future successful authentication. */
export function setPendingDeepLink(link: ParsedDeepLink | null): void {
  pendingDeepLink = link;
}

/** Consumes (returns + clears) the pending link so a link can never be
 * replayed into a second, unintended navigation. */
export function consumePendingDeepLink(): ParsedDeepLink | null {
  const link = pendingDeepLink;
  pendingDeepLink = null;
  return link;
}
