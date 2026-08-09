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

/**
 * Signup copy, which is deliberately NOT the login copy.
 *
 * On login, "no account with that number" must be indistinguishable from "wrong code",
 * because otherwise anyone can enumerate accounts. Signup is different in the one case
 * that matters: the customer has just typed their OWN number, the backend already
 * answers 409 ALREADY_EXISTS with that reason, and hiding it buys no privacy while
 * leaving them stuck on a failing button. So that case is stated, with the next step.
 *
 * Everything else falls back to the same non-committal wording -- and never to the
 * login sentence, which would be nonsense on a screen nobody is signing in from.
 */
export function copyForSignupError(error: unknown): string {
  if (error instanceof DomainError) {
    if (error.telemetryMeta?.backendCode === "ALREADY_EXISTS") {
      return "This mobile number already has an account. Sign in instead.";
    }
    return CATEGORY_COPY[error.category] ?? "We couldn't create your account. Please try again.";
  }
  return "We couldn't create your account. Please try again.";
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
