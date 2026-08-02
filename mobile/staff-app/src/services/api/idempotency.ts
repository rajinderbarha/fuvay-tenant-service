import * as Crypto from "expo-crypto";

/**
 * Central idempotency-key mechanism (Phase F spec section 13). Mirrors the
 * real backend convention: `X-Idempotency-Key` header, checked by
 * app/core/idempotency.py's IdempotencyMiddleware for write methods
 * (POST/PUT/PATCH/DELETE), keyed server-side by
 * sha256(key + path + tenant_id). One key per USER INTENT: retrying the
 * same intent (e.g. resubmitting after a timeout) reuses the same key; a
 * brand-new user action always gets a brand-new key. Keys never encode
 * tenant/customer/job/payment information themselves -- they're opaque.
 */
export function generateIdempotencyKey(): string {
  return Crypto.randomUUID();
}

/**
 * Tracks one key per named "intent" (e.g. "job:j123:start-work") so a
 * retry of that exact intent reuses the key, while a fresh call for a
 * different intent (or the same intent after `clearIntent`, e.g. the
 * technician explicitly starting a NEW attempt rather than retrying) gets
 * a new one. Feature code owns choosing a stable intent id; this module
 * only owns key lifecycle.
 */
export class IdempotencyKeyStore {
  private keys = new Map<string, string>();

  /** Returns the existing key for this intent, or mints and stores a new one. */
  getOrCreateKey(intentId: string): string {
    const existing = this.keys.get(intentId);
    if (existing) return existing;
    const key = generateIdempotencyKey();
    this.keys.set(intentId, key);
    return key;
  }

  /** Forces a new key for this intent (a genuinely new user action, not a retry). */
  newIntent(intentId: string): string {
    const key = generateIdempotencyKey();
    this.keys.set(intentId, key);
    return key;
  }

  clearIntent(intentId: string): void {
    this.keys.delete(intentId);
  }

  clearAll(): void {
    this.keys.clear();
  }
}

export const idempotencyKeyStore = new IdempotencyKeyStore();
