/**
 * Structured domain error architecture. Every failure a screen/hook can
 * encounter is one of these typed categories -- never a raw Error with an
 * unstructured message, and never a raw backend trace/DB detail surfaced
 * to a customer. `diagnostic` is for logs only (never rendered);
 * `telemetryMeta` is safe to attach to an analytics event; `messageKey`
 * is a stable key a future i18n/copy layer resolves to a customer-facing
 * string -- this phase does not own the copy, only the key.
 */
export type DomainErrorCategory =
  | "NETWORK_UNAVAILABLE"
  | "TIMEOUT"
  | "AUTH_REQUIRED"
  | "SESSION_EXPIRED"
  | "ACCOUNT_SUSPENDED"
  | "FORBIDDEN"
  | "VERTICAL_DISABLED"
  | "FEATURE_UNAVAILABLE"
  | "VALIDATION_FAILURE"
  | "SERVICEABILITY_FAILURE"
  | "CONFLICT_STALE_WORKFLOW"
  | "RATE_LIMITED"
  | "BACKEND_UNAVAILABLE"
  | "UNSUPPORTED_APP_VERSION"
  | "CONTRACT_MISMATCH"
  | "UNKNOWN";

export interface DomainErrorInit {
  category: DomainErrorCategory;
  /** Diagnostic detail for logs only -- never render this to a customer,
   * never attach it to a telemetry event verbatim. */
  diagnostic: string;
  /** Safe to attach to an analytics/telemetry event as-is. */
  telemetryMeta?: Record<string, string | number | boolean>;
  /** Stable lookup key for a future customer-facing copy layer. */
  messageKey?: string;
  httpStatus?: number;
  cause?: unknown;
}

export class DomainError extends Error {
  readonly category: DomainErrorCategory;
  readonly diagnostic: string;
  readonly telemetryMeta?: Record<string, string | number | boolean>;
  readonly messageKey?: string;
  readonly httpStatus?: number;

  constructor(init: DomainErrorInit) {
    super(init.diagnostic);
    this.name = "DomainError";
    this.category = init.category;
    this.diagnostic = init.diagnostic;
    this.telemetryMeta = init.telemetryMeta;
    this.messageKey = init.messageKey ?? `error.${init.category.toLowerCase()}`;
    this.httpStatus = init.httpStatus;
    if (init.cause !== undefined) {
      (this as { cause?: unknown }).cause = init.cause;
    }
  }
}

/** Raised by an adapter when a backend payload contains a workflow status
 * this app does not recognize (see domain/status.ts). This must never be
 * silently mapped to the "closest" known status -- that would misrepresent
 * job/booking/quote state to the customer. */
export class UnknownStatusError extends DomainError {
  constructor(field: string, value: string, entityId?: string) {
    super({
      category: "CONTRACT_MISMATCH",
      diagnostic: `Unrecognized ${field} value "${value}"${entityId ? ` on ${entityId}` : ""}`,
      telemetryMeta: { field, value },
      messageKey: "error.contract_mismatch.unknown_status",
    });
    this.name = "UnknownStatusError";
  }
}

/** Raised when a DTO fails runtime schema validation before it ever
 * reaches an adapter. */
export class ContractValidationError extends DomainError {
  constructor(context: string, issues: string[]) {
    super({
      category: "CONTRACT_MISMATCH",
      diagnostic: `Contract validation failed for ${context}: ${issues.join("; ")}`,
      telemetryMeta: { context, issueCount: issues.length },
      messageKey: "error.contract_mismatch.validation",
    });
    this.name = "ContractValidationError";
  }
}

const HTTP_STATUS_CATEGORY: Record<number, DomainErrorCategory> = {
  401: "AUTH_REQUIRED",
  403: "FORBIDDEN",
  408: "TIMEOUT",
  409: "CONFLICT_STALE_WORKFLOW",
  422: "VALIDATION_FAILURE",
  429: "RATE_LIMITED",
};

/** Maps a raw HTTP failure into a DomainError. Backend-specific error
 * codes (e.g. JOB_ASSIGNMENT_CANCEL_NOT_ALLOWED) should be layered on top
 * of this by the calling API module via `telemetryMeta.backendCode` --
 * this function only owns the HTTP-status-shaped part of the mapping. */
export function mapHttpError(status: number | undefined, diagnostic: string, cause?: unknown): DomainError {
  if (status === undefined) {
    return new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic, cause });
  }
  if (status >= 500) {
    return new DomainError({ category: "BACKEND_UNAVAILABLE", diagnostic, httpStatus: status, cause });
  }
  const category = HTTP_STATUS_CATEGORY[status] ?? "UNKNOWN";
  return new DomainError({ category, diagnostic, httpStatus: status, cause });
}
