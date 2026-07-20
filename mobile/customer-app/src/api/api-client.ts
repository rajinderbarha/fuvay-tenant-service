import { environment } from "../config/environment";
import { normalizeApiError, ApiError } from "./api-errors";
import { buildRequestHeaders, resolveAuthToken, handleUnauthorized } from "./request-context";
import { defaultRetryPolicy, type RequestOptions, type HttpMethod } from "./api-types";
import { logger } from "../observability/logger";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryable(method: HttpMethod, idempotencyKey: string | undefined): boolean {
  if (defaultRetryPolicy.retryableMethods.includes(method)) return true;
  return Boolean(idempotencyKey);
}

async function performRequest<T>(path: string, options: RequestOptions): Promise<T> {
  const method = options.method ?? "GET";
  const headers = await buildRequestHeaders(options.headers);

  if (!options.skipAuth) {
    const token = await resolveAuthToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? environment.apiTimeoutMs;
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

  // Allow the caller to also cancel (e.g. screen unmount) without losing the timeout abort.
  if (options.signal) {
    options.signal.addEventListener("abort", () => controller.abort());
  }

  const requestId = headers["X-Request-Id"];

  try {
    logger.debug("api.request", { method, path, requestId });

    const res = await fetch(`${environment.apiBaseUrl}${path}`, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });

    if (!res.ok) {
      const error = normalizeApiError(null, { status: res.status, requestId });
      logger.warn("api.error", { method, path, requestId, status: res.status, category: error.category });
      throw error;
    }

    if (res.status === 204) return undefined as T;

    const json = await res.json();
    return (json?.data ?? json) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    const normalized = normalizeApiError(err instanceof Error && err.name === "AbortError" && !options.signal?.aborted ? new Error("timeout") : err, {
      requestId,
    });
    logger.warn("api.error", { method, path, requestId, category: normalized.category });
    throw normalized;
  } finally {
    clearTimeout(timeoutHandle);
  }
}

/**
 * Multipart upload — deliberately separate from `performRequest`/JSON
 * bodies. Never JSON.stringify's `formData`, and strips the default
 * `Content-Type: application/json` header so `fetch` can set its own
 * `multipart/form-data; boundary=...` header (setting it manually breaks
 * the boundary). No retry-on-failure: a partially-sent multipart body
 * cannot be safely replayed by this generic layer — CUSTOMER-L5-06's
 * upload coordinator (`media-upload-session.ts`) owns its own,
 * upload-aware retry instead. Still gets exactly one 401-refresh-and-retry,
 * matching every other authenticated request in this app.
 */
async function performMultipartRequest<T>(path: string, formData: FormData, options: RequestOptions, allowUnauthorizedRetry = true): Promise<T> {
  const headers = await buildRequestHeaders(options.headers);
  delete headers["Content-Type"];

  if (!options.skipAuth) {
    const token = await resolveAuthToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? environment.apiTimeoutMs;
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  if (options.signal) {
    options.signal.addEventListener("abort", () => controller.abort());
  }

  const requestId = headers["X-Request-Id"];

  try {
    logger.debug("api.upload_request", { path, requestId });

    const res = await fetch(`${environment.apiBaseUrl}${path}`, {
      method: options.method ?? "POST",
      headers,
      body: formData,
      signal: controller.signal,
    });

    if (!res.ok) {
      const error = normalizeApiError(null, { status: res.status, requestId });
      logger.warn("api.upload_error", { path, requestId, status: res.status, category: error.category });

      if (allowUnauthorizedRetry && !options.skipAuth && error.category === "unauthorized") {
        const refreshed = await handleUnauthorized();
        if (refreshed) return performMultipartRequest<T>(path, formData, options, false);
      }
      throw error;
    }

    const json = await res.json();
    return (json?.data ?? json) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    const normalized = normalizeApiError(err instanceof Error && err.name === "AbortError" && !options.signal?.aborted ? new Error("timeout") : err, {
      requestId,
    });
    logger.warn("api.upload_error", { path, requestId, category: normalized.category });
    throw normalized;
  } finally {
    clearTimeout(timeoutHandle);
  }
}

async function requestWithRetry<T>(path: string, options: RequestOptions, allowUnauthorizedRetry = true): Promise<T> {
  const method = options.method ?? "GET";
  const maxAttempts = isRetryable(method, options.idempotencyKey) ? defaultRetryPolicy.maxAttempts : 1;

  let lastError: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await performRequest<T>(path, options);
    } catch (err) {
      lastError = err;

      // A 401 gets exactly one chance to refresh-and-retry — never inside
      // the retry loop itself (that would multiply refresh attempts by
      // maxAttempts) and never for a request that opted out of auth
      // (skipAuth) or is itself the refresh/retry attempt.
      if (allowUnauthorizedRetry && !options.skipAuth && err instanceof ApiError && err.category === "unauthorized") {
        const refreshed = await handleUnauthorized();
        if (refreshed) return requestWithRetry<T>(path, options, false);
      }

      const retryable = err instanceof ApiError && err.retryable;
      if (!retryable || attempt === maxAttempts) throw err;
      await sleep(defaultRetryPolicy.baseDelayMs * attempt);
    }
  }
  throw lastError;
}

export const apiClient = {
  get: <T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}) => requestWithRetry<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options: Omit<RequestOptions, "method" | "body"> = {}) =>
    requestWithRetry<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options: Omit<RequestOptions, "method" | "body"> = {}) =>
    requestWithRetry<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options: Omit<RequestOptions, "method" | "body"> = {}) =>
    requestWithRetry<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}) => requestWithRetry<T>(path, { ...options, method: "DELETE" }),
  uploadMultipart: <T>(path: string, formData: FormData, options: Omit<RequestOptions, "method" | "body"> = {}) =>
    performMultipartRequest<T>(path, formData, { ...options, method: "POST" }),
};
