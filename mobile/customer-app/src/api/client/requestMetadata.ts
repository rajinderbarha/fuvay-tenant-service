import * as Crypto from "expo-crypto";

/** One request ID per outgoing call -- distinct from any backend-returned
 * correlation ID (see responseParser.ts), sent as `X-Request-ID` so client
 * and server logs can be joined even when the server rejects the request
 * before generating its own. */
export function generateRequestId(): string {
  return Crypto.randomUUID();
}

/** High-entropy idempotency key generator (Phase F section 25 / Phase D
 * offline.ts IDEMPOTENT_MUTATION class). Scoped per logical operation by
 * the caller -- this function only guarantees entropy, never uniqueness
 * scope, which is the caller's responsibility (see api/idempotency). */
export function generateIdempotencyKey(): string {
  return Crypto.randomUUID();
}
