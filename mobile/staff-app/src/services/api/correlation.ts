/**
 * Request correlation (Phase F spec section 4). Mirrors the real backend
 * convention: RequestIDMiddleware honors a client-sent `X-Request-ID` and
 * always echoes one back (app/middleware.py). We always send one so a
 * cold request and its retry/replay share a traceable ID in logs on both
 * sides.
 */
export function generateCorrelationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `req_${crypto.randomUUID()}`;
  }
  // RN/Hermes fallback -- not cryptographically strong, fine for a
  // trace-correlation ID (unlike idempotency keys, which use expo-crypto).
  const rand = Math.random().toString(16).slice(2) + Date.now().toString(16);
  return `req_${rand}`;
}
