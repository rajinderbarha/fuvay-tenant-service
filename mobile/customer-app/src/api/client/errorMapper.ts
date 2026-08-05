import { DomainError, DomainErrorCategory, mapHttpError } from "../../domain/errors";

/**
 * Backend error-code → DomainError category overrides. `mapHttpError`
 * (Phase D) already covers the generic HTTP-status shape; this table
 * layers the SPECIFIC ServiceOSException codes this phase's auth audit
 * confirmed exist in source (app/engines/auth/service.py /
 * app/exceptions.py) onto the right category, since a 401 body can mean
 * very different things ("wrong password" vs "token reuse detected").
 */
const BACKEND_CODE_CATEGORY: Record<string, DomainErrorCategory> = {
  UNAUTHORIZED: "AUTH_REQUIRED",
  INVALID_TOKEN: "SESSION_EXPIRED",
  TOKEN_EXPIRED: "SESSION_EXPIRED",
  // Confirmed in AuthService.refresh_token: raised when a refresh token
  // that was already rotated is presented again -- the whole family is
  // revoked server-side. This must terminate the session, never retry.
  TOKEN_BLACKLISTED: "SESSION_EXPIRED",
  ACCOUNT_LOCKED: "ACCOUNT_SUSPENDED",
  MFA_POLICY_REQUIRED: "FORBIDDEN",
};

/**
 * Matches the backend's RFC 7807 problem+json shape exactly
 * (app/schemas/base.py `ProblemDetail`) -- every ServiceOS error uses
 * this, never a bespoke shape. Clients must switch on `error_code`, never
 * on HTTP status alone (the backend's own stated contract).
 */
export interface ApiErrorBody {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string | null;
  error_code?: string;
  blocking_rule?: string | null;
  resolution?: string | null;
  request_id?: string | null;
  context?: Record<string, unknown> | null;
}

export interface MapApiErrorInput {
  httpStatus: number | undefined;
  body?: ApiErrorBody;
  diagnostic: string;
  cause?: unknown;
}

/**
 * Single normalization point for every API failure this app sees. Never
 * exposes `body` verbatim as the diagnostic if it might contain a stack
 * trace or SQL detail -- only `message` (already customer-safe per
 * backend convention: `ServiceOSException.message`) and `code` pass
 * through into telemetryMeta.
 */
export function mapApiError({ httpStatus, body, diagnostic, cause }: MapApiErrorInput): DomainError {
  const backendCode = body?.error_code;
  const safeDetail = body?.detail ?? diagnostic;

  if (backendCode && BACKEND_CODE_CATEGORY[backendCode]) {
    return new DomainError({
      category: BACKEND_CODE_CATEGORY[backendCode],
      diagnostic: safeDetail,
      httpStatus,
      telemetryMeta: { backendCode },
      cause,
    });
  }
  if (httpStatus === 429) {
    // Confirmed in app/core/security.py RateLimiter.check_and_raise --
    // retry_after_seconds lives in the RFC 7807 `context` object, not a
    // top-level field.
    const retryAfterSeconds = body?.context?.retry_after_seconds;
    return new DomainError({
      category: "RATE_LIMITED",
      diagnostic: safeDetail,
      httpStatus,
      telemetryMeta: {
        backendCode: backendCode ?? "RATE_LIMITED",
        ...(typeof retryAfterSeconds === "number" ? { retryAfterSeconds } : {}),
      },
      cause,
    });
  }
  if (httpStatus === 409) {
    // DUPLICATE_OPEN_REQUEST (app/engines/compliance/customer_router.py
    // create_my_request) carries `existing_request_id` in `context` so the
    // client can route straight to the already-open request instead of
    // just showing an error.
    const existingRequestId = body?.context?.existing_request_id;
    return new DomainError({
      category: "CONFLICT_STALE_WORKFLOW",
      diagnostic: safeDetail,
      httpStatus,
      telemetryMeta: {
        ...(backendCode ? { backendCode } : {}),
        ...(typeof existingRequestId === "string" ? { existingRequestId } : {}),
      },
      cause,
    });
  }
  const mapped = mapHttpError(httpStatus, safeDetail, cause);
  if (backendCode) {
    return new DomainError({
      category: mapped.category,
      diagnostic: mapped.diagnostic,
      httpStatus: mapped.httpStatus,
      telemetryMeta: { backendCode },
      cause,
    });
  }
  return mapped;
}
