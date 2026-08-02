import { AppError } from "./types";
import { isOffline } from "./networkState";

/**
 * Bounded exponential backoff with jitter (Phase F spec section 12).
 * Retry eligibility is decided from AppError.retryable + AppError.category
 * ONLY -- auth/permission/validation/conflict/not-found errors are never
 * retried here regardless of call site.
 */
export interface RetryDecision { shouldRetry: boolean; delayMs: number }

const MAX_ATTEMPTS = 3;
const BASE_DELAY_MS = 400;
const MAX_DELAY_MS = 4_000;

export function getRetryDecision(error: AppError, attempt: number, unsafeToRetry: boolean): RetryDecision {
  if (unsafeToRetry) return { shouldRetry: false, delayMs: 0 };
  if (attempt >= MAX_ATTEMPTS) return { shouldRetry: false, delayMs: 0 };
  if (isOffline()) return { shouldRetry: false, delayMs: 0 };

  if (error.category === "rate_limit" && typeof error.retryAfterSeconds === "number") {
    return { shouldRetry: true, delayMs: error.retryAfterSeconds * 1000 };
  }
  if (!error.retryable) return { shouldRetry: false, delayMs: 0 };

  const exponential = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** (attempt - 1));
  const jitter = Math.random() * exponential * 0.25;
  return { shouldRetry: true, delayMs: exponential + jitter };
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
