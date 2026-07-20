export type ParsedDeepLinkSource = "custom-scheme" | "universal-link" | "app-link" | "unknown";

export interface ParsedDeepLink {
  raw: string;
  scheme: string;
  host: string;
  path: string;
  query: Record<string, string>;
  source: ParsedDeepLinkSource;
}

export interface DeepLinkParseFailure {
  ok: false;
  reason: "oversized_url" | "malformed_url";
}

export interface DeepLinkParseSuccess {
  ok: true;
  link: ParsedDeepLink;
}

const MAX_URL_LENGTH = 2048;

const TRUSTED_UNIVERSAL_HOSTS = ["app.serviceos.in"];

function classifySource(scheme: string, host: string): ParsedDeepLinkSource {
  if (scheme === "https" || scheme === "http") {
    return TRUSTED_UNIVERSAL_HOSTS.includes(host) ? "universal-link" : "unknown";
  }
  if (scheme === "serviceos") return "custom-scheme";
  return "unknown";
}

/**
 * Pure parsing only — no validation of whether the resulting route/params
 * are *allowed* (that's deep-link-validator.ts). This function only turns a
 * raw string into a structured shape, or reports why it couldn't.
 */
export function parseDeepLink(rawUrl: string): DeepLinkParseSuccess | DeepLinkParseFailure {
  if (rawUrl.length > MAX_URL_LENGTH) {
    return { ok: false, reason: "oversized_url" };
  }

  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return { ok: false, reason: "malformed_url" };
  }

  const query: Record<string, string> = {};
  url.searchParams.forEach((value, key) => {
    query[key] = value;
  });

  const scheme = url.protocol.replace(":", "");
  const isHttpFamily = scheme === "https" || scheme === "http";
  // For a custom scheme, the WHATWG URL parser treats the first path segment
  // as "hostname" (e.g. "serviceos://bookings/abc" -> hostname="bookings",
  // pathname="/abc") — that segment is semantically part of our route path,
  // not a real host, so it's folded back in. For http(s) universal links the
  // hostname is a real domain and must stay separate from the path.
  const host = isHttpFamily ? url.hostname : "";
  const path = (isHttpFamily ? url.pathname : `${url.hostname}${url.pathname}`).replace(/^\/+/, "").replace(/\/+$/, "");

  return {
    ok: true,
    link: { raw: rawUrl, scheme, host, path, query, source: classifySource(scheme, url.hostname) },
  };
}
