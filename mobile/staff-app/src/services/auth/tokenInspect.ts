/**
 * Local, UNVERIFIED JWT payload decoding (Phase F spec section 7: "Local
 * token parsing may be used only for expiry optimization, never
 * authorization"). This never checks the signature and must never be used
 * to decide whether a request is authorized -- only to avoid an
 * unnecessary network round-trip when a token is obviously already
 * expired. Every actual authorization decision still goes through the
 * backend (validateSession / the API layer's 401 handling).
 */
function base64UrlDecode(segment: string): string {
  const padded = segment.replace(/-/g, "+").replace(/_/g, "/").padEnd(segment.length + ((4 - (segment.length % 4)) % 4), "=");
  if (typeof atob === "function") return atob(padded);
  // eslint-disable-next-line no-undef
  return Buffer.from(padded, "base64").toString("utf-8");
}

/** Returns the token's `exp` claim as an ISO 8601 string, or null if the
 * token can't be parsed (malformed/not a JWT) -- never throws. */
export function decodeAccessTokenExpiry(token: string | null): string | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(base64UrlDecode(parts[1])) as { exp?: number };
    if (typeof payload.exp !== "number") return null;
    return new Date(payload.exp * 1000).toISOString();
  } catch {
    return null;
  }
}
