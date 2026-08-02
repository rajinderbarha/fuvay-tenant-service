/**
 * Shared networking types (Phase F spec sections 10-14). Mirrors the REAL
 * backend envelope shapes (app/schemas/base.py ApiResponse / ProblemDetail /
 * ValidationProblemDetail) -- not invented response shapes.
 */

export interface ApiMeta {
  request_id: string;
  timestamp: string;
  version: string;
  engine_id?: string | null;
  tenant_id?: string | null;
  idempotent?: boolean;
}

export interface ApiLink { href: string; method: string; rel: string; description?: string | null }
export interface ApiLinks { self?: string | null; collection?: string | null; related?: Record<string, string> | null; actions?: ApiLink[] | null }

/** The real success envelope every endpoint returns (app/schemas/base.py ApiResponse). */
export interface ApiSuccessEnvelope<T> {
  success: true;
  data: T;
  links?: ApiLinks | null;
  meta: ApiMeta;
}

export interface ValidationErrorItem { field: string; message: string; received?: unknown; expected?: string | null }

/** The real RFC 7807 error envelope (app/exceptions.py / ProblemDetail). */
export interface ProblemDetailBody {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string | null;
  error_code: string;
  blocking_rule?: string | null;
  resolution?: string | null;
  request_id?: string | null;
  context?: Record<string, unknown> | null;
  errors?: ValidationErrorItem[];
}

/** Normalized client-facing error categories (spec section 10). Client
 * aliases exist ONLY in errorMapper.ts -- nowhere else re-derives a code. */
export type AppErrorCode =
  | "AUTH_REQUIRED" | "ACCESS_TOKEN_EXPIRED" | "REFRESH_TOKEN_EXPIRED" | "REFRESH_TOKEN_REUSED"
  | "SESSION_REVOKED" | "SESSION_NOT_FOUND" | "MFA_REQUIRED" | "ACCOUNT_PENDING" | "ACCOUNT_SUSPENDED"
  | "TENANT_INACTIVE" | "TECHNICIAN_INACTIVE" | "WRONG_AUDIENCE" | "ROLE_NOT_ALLOWED" | "CAPABILITY_REQUIRED"
  | "ENTITY_NOT_ASSIGNED" | "ACTION_NOT_ALLOWED" | "RATE_LIMITED" | "VALIDATION_ERROR" | "CONFLICT"
  | "STALE_ENTITY_VERSION" | "STALE_WORKFLOW_VERSION" | "QUOTE_NOT_CURRENT"
  | "JOB_TYPE_CONTEXT_UNRESOLVED" | "APPROVED_ESTIMATE_IMMUTABLE" | "VERTICAL_DISABLED" | "MEDIA_STORAGE_UNAVAILABLE"
  | "NETWORK_OFFLINE" | "NETWORK_TIMEOUT" | "SERVER_UNAVAILABLE" | "REQUEST_CANCELLED" | "UNKNOWN_API_ERROR";

export type AppErrorCategory = "auth" | "permission" | "validation" | "conflict" | "rate_limit" | "network" | "server" | "cancelled" | "unknown";

export interface AppError {
  code: AppErrorCode;
  category: AppErrorCategory;
  /** Safe to render directly to the technician -- never a raw backend trace. */
  safeMessage: string;
  fieldErrors?: ValidationErrorItem[];
  httpStatus?: number;
  retryable: boolean;
  correlationId?: string;
  retryAfterSeconds?: number;
  /** The real backend error_code when one was present -- retained for
   * telemetry/debugging, never shown to the user directly. */
  backendCode?: string;
  /** Development-only diagnostic detail. Never rendered, never sent to
   * production telemetry as-is (redact first). */
  cause?: unknown;
}

export interface RequestConcurrencyContract {
  entityVersion?: number;
  workflowVersion?: number;
  quoteVersion?: number;
  quoteId?: string;
}

export type NetworkState = "unknown" | "online" | "offline" | "internet_reachable_false" | "reconnecting";

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
  idempotencyKey?: string;
  concurrency?: RequestConcurrencyContract;
  timeoutMs?: number;
  /** Marks a mutation as unsafe to auto-retry even on a transient network
   * failure (spec section 12) -- distinct from idempotency-key eligibility. */
  unsafeToRetry?: boolean;
}

export type ApiResult<T> = { ok: true; data: T; meta: ApiMeta; links?: ApiLinks | null } | { ok: false; error: AppError };
