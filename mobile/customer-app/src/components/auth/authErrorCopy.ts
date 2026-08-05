import { DomainError, DomainErrorCategory } from "../../domain/errors";

/**
 * Maps a DomainErrorCategory to customer-safe screen copy for the
 * authentication flow (spec section 20). Never surfaces `diagnostic`
 * directly -- that field may contain a backend `detail` string that,
 * while itself customer-safe per backend convention, is not vetted for
 * this specific screen's tone; this table is the one place auth-screen
 * wording is decided.
 */
const CATEGORY_COPY: Partial<Record<DomainErrorCategory, string>> = {
  NETWORK_UNAVAILABLE: "You're offline. Check your connection and try again.",
  TIMEOUT: "That took too long. Please try again.",
  RATE_LIMITED: "Too many attempts. Please wait a moment and try again.",
  BACKEND_UNAVAILABLE: "We can't reach Fuvay right now. Please try again shortly.",
  CONTRACT_MISMATCH: "Something went wrong on our end. Please try again.",
  ACCOUNT_SUSPENDED: "This account is locked. Try again later or contact support.",
  SESSION_EXPIRED: "That code has expired. Request a new one.",
  VALIDATION_FAILURE: "Please check the details you entered.",
};

const ENUMERATION_SAFE_DEFAULT = "We couldn't sign you in with those details.";

export function copyForAuthError(error: unknown): string {
  if (error instanceof DomainError) {
    return CATEGORY_COPY[error.category] ?? ENUMERATION_SAFE_DEFAULT;
  }
  return ENUMERATION_SAFE_DEFAULT;
}

export function isRateLimited(error: unknown): error is DomainError {
  return error instanceof DomainError && error.category === "RATE_LIMITED";
}

export function retryAfterSecondsOf(error: unknown): number | undefined {
  if (error instanceof DomainError && typeof error.telemetryMeta?.retryAfterSeconds === "number") {
    return error.telemetryMeta.retryAfterSeconds;
  }
  return undefined;
}
