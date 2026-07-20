export type ApiErrorCategory =
  | "network_error"
  | "timeout"
  | "cancelled"
  | "validation_error"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "rate_limited"
  | "server_error"
  | "maintenance"
  | "unknown_error";

export class ApiError extends Error {
  readonly category: ApiErrorCategory;
  readonly status?: number;
  readonly requestId?: string;
  readonly retryable: boolean;

  constructor(params: { category: ApiErrorCategory; message: string; status?: number; requestId?: string; retryable?: boolean }) {
    super(params.message);
    this.name = "ApiError";
    this.category = params.category;
    this.status = params.status;
    this.requestId = params.requestId;
    this.retryable = params.retryable ?? false;
  }
}

function categoryFromStatus(status: number): ApiErrorCategory {
  if (status === 400 || status === 422) return "validation_error";
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 429) return "rate_limited";
  if (status === 503) return "maintenance";
  if (status >= 500) return "server_error";
  return "unknown_error";
}

/**
 * Normalizes any failure from the API client into a stable ApiError. Never
 * forwards raw server stack traces — only a safe, generic message is kept
 * for user-facing categories; the original message is preserved solely for
 * developer-facing categories (network/unknown) where it carries no server detail.
 */
export function normalizeApiError(input: unknown, opts: { status?: number; requestId?: string } = {}): ApiError {
  if (input instanceof ApiError) return input;

  if (input instanceof DOMException && input.name === "AbortError") {
    return new ApiError({ category: "cancelled", message: "Request was cancelled." });
  }

  if (input instanceof Error && /timeout/i.test(input.message)) {
    return new ApiError({ category: "timeout", message: "The request timed out.", retryable: true });
  }

  if (typeof opts.status === "number") {
    const category = categoryFromStatus(opts.status);
    const retryable = category === "rate_limited" || category === "server_error" || category === "maintenance";
    return new ApiError({
      category,
      message: safeMessageForCategory(category),
      status: opts.status,
      requestId: opts.requestId,
      retryable,
    });
  }

  if (input instanceof TypeError) {
    // fetch() throws a plain TypeError for DNS/connection failures.
    return new ApiError({ category: "network_error", message: "Network request failed.", retryable: true });
  }

  return new ApiError({ category: "unknown_error", message: "Something went wrong.", requestId: opts.requestId });
}

function safeMessageForCategory(category: ApiErrorCategory): string {
  switch (category) {
    case "validation_error":
      return "The request contained invalid data.";
    case "unauthorized":
      return "You need to sign in again.";
    case "forbidden":
      return "You don't have permission to do that.";
    case "not_found":
      return "We couldn't find what you were looking for.";
    case "conflict":
      return "This conflicts with existing data.";
    case "rate_limited":
      return "Too many requests. Please try again shortly.";
    case "maintenance":
      return "The service is temporarily unavailable.";
    case "server_error":
      return "Something went wrong on our end.";
    default:
      return "Something went wrong.";
  }
}
