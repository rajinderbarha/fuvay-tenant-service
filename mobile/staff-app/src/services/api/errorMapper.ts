import { AppError, AppErrorCode, AppErrorCategory, ProblemDetailBody } from "./types";

/**
 * The ONE place a raw backend/network failure becomes a typed AppError
 * (Phase F spec sections 10-11). Backend codes are used verbatim where
 * they exist (confirmed against app/exceptions.py's ERROR_CODES registry
 * and app/dependencies/auth.py) -- this file is the only alias layer, nothing
 * downstream re-derives a code from a status number or a message substring.
 *
 * `context` disambiguates backend codes that are intentionally reused for
 * different situations server-side (e.g. TOKEN_BLACKLISTED is raised both
 * for a normal logged-out session AND for detected refresh-token reuse --
 * same backend code, different client meaning depending on which endpoint
 * produced it).
 */
export type ErrorMapperContext = "public" | "authenticated" | "refresh";

const GENERIC_SERVER_MESSAGE = "Something went wrong on our end. Please try again.";
const GENERIC_NETWORK_MESSAGE = "Couldn't reach Fuvay. Check your connection and try again.";

function categoryFor(code: AppErrorCode): AppErrorCategory {
  switch (code) {
    case "AUTH_REQUIRED": case "ACCESS_TOKEN_EXPIRED": case "REFRESH_TOKEN_EXPIRED":
    case "REFRESH_TOKEN_REUSED": case "SESSION_REVOKED": case "SESSION_NOT_FOUND":
    case "MFA_REQUIRED": case "ACCOUNT_PENDING": case "ACCOUNT_SUSPENDED":
    case "TENANT_INACTIVE": case "TECHNICIAN_INACTIVE": case "WRONG_AUDIENCE":
      return "auth";
    case "ROLE_NOT_ALLOWED": case "CAPABILITY_REQUIRED": case "ENTITY_NOT_ASSIGNED": case "ACTION_NOT_ALLOWED":
    case "VERTICAL_DISABLED":
      return "permission";
    case "VALIDATION_ERROR": case "JOB_TYPE_CONTEXT_UNRESOLVED":
      return "validation";
    case "CONFLICT": case "STALE_ENTITY_VERSION": case "STALE_WORKFLOW_VERSION": case "QUOTE_NOT_CURRENT":
    case "APPROVED_ESTIMATE_IMMUTABLE":
      return "conflict";
    case "RATE_LIMITED":
      return "rate_limit";
    case "NETWORK_OFFLINE": case "NETWORK_TIMEOUT":
      return "network";
    case "SERVER_UNAVAILABLE": case "MEDIA_STORAGE_UNAVAILABLE":
      return "server";
    case "REQUEST_CANCELLED":
      return "cancelled";
    default:
      return "unknown";
  }
}

const RETRYABLE_CODES = new Set<AppErrorCode>([
  "NETWORK_TIMEOUT", "SERVER_UNAVAILABLE", "RATE_LIMITED",
]);

/** Backend error_code -> AppErrorCode, split by call-site context where the
 * same backend code is intentionally reused for different situations. */
function mapBackendCode(code: string, context: ErrorMapperContext): AppErrorCode {
  switch (code) {
    case "UNAUTHORIZED":
      return "AUTH_REQUIRED";
    case "INVALID_TOKEN":
      return context === "refresh" ? "REFRESH_TOKEN_EXPIRED" : "ACCESS_TOKEN_EXPIRED";
    case "TOKEN_EXPIRED":
      return "REFRESH_TOKEN_EXPIRED";
    case "TOKEN_BLACKLISTED":
      return context === "refresh" ? "REFRESH_TOKEN_REUSED" : "SESSION_REVOKED";
    case "SESSION_REVOKED":
      return "SESSION_REVOKED";
    case "ACCOUNT_LOCKED":
      return "ACCOUNT_SUSPENDED";
    case "MFA_REQUIRED":
    case "MFA_SETUP_REQUIRED":
      return "MFA_REQUIRED";
    case "PERMISSION_DENIED":
      return "CAPABILITY_REQUIRED";
    case "TENANT_SUSPENDED":
    case "TENANT_TERMINATED":
    case "TENANT_TRIAL_EXPIRED":
      return "TENANT_INACTIVE";
    case "VALIDATION_ERROR":
      return "VALIDATION_ERROR";
    case "RATE_LIMITED":
      return "RATE_LIMITED";
    case "CONFLICT":
      return "CONFLICT";
    case "NOT_FOUND":
    case "TENANT_NOT_FOUND":
      return "SESSION_NOT_FOUND";
    // The exact strings the execution engine raises verbatim (confirmed
    // via app/engines/execution/*_service.py's ENTITY_NOT_ASSIGNED 403s on
    // estimate/work-execution/direct-payment mutations, and
    // app/engines/execution/constants.py's ERR_JOB_TYPE_CONTEXT_UNRESOLVED) --
    // used as-is, never re-derived from a status code alone.
    case "ENTITY_NOT_ASSIGNED":
      return "ENTITY_NOT_ASSIGNED";
    case "JOB_TYPE_CONTEXT_UNRESOLVED":
      return "JOB_TYPE_CONTEXT_UNRESOLVED";
    // app/engines/quote_checklist/constants.py's real codes.
    case "QUOTE_NOT_CURRENT":
      return "QUOTE_NOT_CURRENT";
    case "APPROVED_ESTIMATE_IMMUTABLE":
      return "APPROVED_ESTIMATE_IMMUTABLE";
    // app/dependencies/vertical_directory_scope.py's real code.
    case "VERTICAL_DISABLED":
      return "VERTICAL_DISABLED";
    // app/engines/media/storage.py's real code (not the assumed
    // "STORAGE_UNAVAILABLE" -- the backend's actual string is more specific).
    case "MEDIA_STORAGE_UNAVAILABLE":
      return "MEDIA_STORAGE_UNAVAILABLE";
    // app/engines/home_service_assignment/constants.py's real code (the
    // backend's actual string, not a generic "ROLE_NOT_ALLOWED" guess).
    case "JOB_ASSIGNMENT_ROLE_NOT_ALLOWED":
      return "ROLE_NOT_ALLOWED";
    default:
      // Forward-compatible bucket for the various per-engine
      // "*_STALE_VERSION" codes (e.g. DIRECT_PAYMENT_STALE_VERSION) -- the
      // backend has no single shared code for this family yet (each engine
      // defines its own), so this is a deliberate, narrow, documented
      // exception to "no substring matching", not a general-purpose one.
      if (code.endsWith("_STALE_VERSION")) return "STALE_ENTITY_VERSION";
      return "UNKNOWN_API_ERROR";
  }
}

export function mapProblemDetail(problem: ProblemDetailBody, context: ErrorMapperContext, correlationId?: string): AppError {
  const code = mapBackendCode(problem.error_code, context);
  const category = categoryFor(code);
  const retryAfterSeconds = typeof problem.context?.retry_after_seconds === "number" ? problem.context.retry_after_seconds : undefined;

  return {
    code,
    category,
    safeMessage: code === "UNKNOWN_API_ERROR" && problem.status >= 500 ? GENERIC_SERVER_MESSAGE : problem.detail,
    fieldErrors: problem.errors,
    httpStatus: problem.status,
    retryable: RETRYABLE_CODES.has(code) || (code === "UNKNOWN_API_ERROR" && problem.status >= 500),
    correlationId: problem.request_id ?? correlationId,
    retryAfterSeconds,
    backendCode: problem.error_code,
  };
}

export function mapNetworkFailure(kind: "offline" | "timeout" | "abort", correlationId?: string): AppError {
  if (kind === "abort") {
    return { code: "REQUEST_CANCELLED", category: "cancelled", safeMessage: "Request cancelled.", retryable: false, correlationId };
  }
  if (kind === "timeout") {
    return { code: "NETWORK_TIMEOUT", category: "network", safeMessage: GENERIC_NETWORK_MESSAGE, retryable: true, correlationId };
  }
  return { code: "NETWORK_OFFLINE", category: "network", safeMessage: GENERIC_NETWORK_MESSAGE, retryable: true, correlationId };
}

/** Unparseable body / non-JSON / unexpected shape -- never crash the caller. */
export function mapUnknownFailure(httpStatus: number | undefined, correlationId?: string, cause?: unknown): AppError {
  const retryable = typeof httpStatus === "number" && httpStatus >= 500;
  return {
    code: retryable ? "SERVER_UNAVAILABLE" : "UNKNOWN_API_ERROR",
    category: retryable ? "server" : "unknown",
    safeMessage: GENERIC_SERVER_MESSAGE,
    httpStatus,
    retryable,
    correlationId,
    cause: __DEV__ ? cause : undefined,
  };
}
