import { DomainError } from "../../domain/errors";

/**
 * Conservative retry policy (spec section 24). Only network-before-
 * response failures and a narrow set of transient server categories are
 * ever eligible; every authentication endpoint and every online-only
 * mutation (Phase D domain/offline.ts) is explicitly excluded by the
 * caller never invoking this for those requests -- see authApi.ts, which
 * never wraps its calls in `withRetry`.
 */
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

const RETRYABLE_CATEGORIES = new Set(["NETWORK_UNAVAILABLE", "TIMEOUT", "BACKEND_UNAVAILABLE"]);

export interface RetryPolicyOptions {
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

const DEFAULTS: Required<RetryPolicyOptions> = { maxAttempts: 3, baseDelayMs: 250, maxDelayMs: 4000 };

export function isRetryableError(error: unknown, method: HttpMethod): boolean {
  if (method !== "GET") return false; // idempotent-mutation retries go through a separate explicit path (idempotency module), never this generic policy
  if (!(error instanceof DomainError)) return false;
  return RETRYABLE_CATEGORIES.has(error.category);
}

/** Bounded exponential backoff with jitter. Pure function -- the caller
 * owns the actual `setTimeout`/loop so this stays trivially testable. */
export function computeBackoffMs(attempt: number, options: RetryPolicyOptions = {}): number {
  const { baseDelayMs, maxDelayMs } = { ...DEFAULTS, ...options };
  const exp = Math.min(maxDelayMs, baseDelayMs * 2 ** (attempt - 1));
  const jitter = Math.random() * exp * 0.2;
  return Math.round(exp * 0.8 + jitter);
}

export function getMaxAttempts(options: RetryPolicyOptions = {}): number {
  return { ...DEFAULTS, ...options }.maxAttempts;
}
