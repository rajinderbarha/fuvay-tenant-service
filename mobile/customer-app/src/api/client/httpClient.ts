import { ENV } from "../../config/environment";
import { isOffline } from "../networkState";
import { generateRequestId } from "./requestMetadata";
import { createTimeoutSignal, RequestCancelledError } from "./cancellation";
import { mapApiError, ApiErrorBody } from "./errorMapper";
import { DomainError } from "../../domain/errors";
import { redact } from "../../utils/redact";
import { logger } from "../../utils/logger";

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method: HttpMethod;
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
  accessToken?: string | null;
  idempotencyKey?: string;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export interface RawResponse {
  status: number;
  json: unknown;
  requestId: string | undefined;
}

function buildUrl(path: string): string {
  // Prevents accidental double slashes regardless of whether the caller
  // includes a leading slash (spec section 7).
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${ENV.apiBaseUrl}${normalizedPath}`;
}

/**
 * Canonical HTTP transport (spec section 9). Deliberately has NO
 * knowledge of refresh/session orchestration -- that lives in
 * api/session/refreshCoordinator.ts, which wraps this client. Screens
 * never call this directly; they go through typed endpoint modules
 * (api/auth/authApi.ts, future feature modules).
 */
export async function request({
  method, path, body, headers = {}, accessToken, idempotencyKey, signal, timeoutMs = ENV.apiTimeoutMs,
}: RequestOptions): Promise<RawResponse> {
  if (isOffline()) {
    throw new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "Device is offline" });
  }

  const requestId = generateRequestId();

  // Multipart uploads (photo attachments) must NOT carry a caller-set
  // Content-Type: the runtime has to generate its own `multipart/form-data`
  // header including the boundary token, and an explicit
  // "application/json" here would both override that and mislabel the body.
  const isMultipart = typeof FormData !== "undefined" && body instanceof FormData;

  const finalHeaders: Record<string, string> = {
    ...(isMultipart ? {} : { "Content-Type": "application/json" }),
    Accept: "application/json",
    "X-Request-ID": requestId,
    ...headers,
  };
  if (accessToken) finalHeaders.Authorization = `Bearer ${accessToken}`;
  if (idempotencyKey) finalHeaders["Idempotency-Key"] = idempotencyKey;

  const { signal: timeoutSignal, clear: clearTimeoutSignal } = createTimeoutSignal(timeoutMs, signal);

  logger.debug("http.request", redact({ method, path, requestId }));

  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      method,
      headers: finalHeaders,
      // FormData is passed through untouched; JSON.stringify would turn it
      // into "[object FormData]" and the upload would arrive empty.
      body: body === undefined ? undefined : isMultipart ? (body as FormData) : JSON.stringify(body),
      signal: timeoutSignal,
    });
  } catch (err) {
    if (timeoutSignal.aborted) {
      if (signal?.aborted) throw new RequestCancelledError("caller_signal");
      throw new DomainError({ category: "TIMEOUT", diagnostic: `Request timed out after ${timeoutMs}ms`, cause: err });
    }
    throw new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "Network request failed", cause: err });
  } finally {
    clearTimeoutSignal();
  }

  const responseRequestId = response.headers.get("X-Request-ID") ?? response.headers.get("x-request-id") ?? undefined;

  let json: unknown = null;
  const rawText = await response.text();
  if (rawText) {
    try {
      json = JSON.parse(rawText);
    } catch (err) {
      if (response.ok) {
        throw new DomainError({ category: "CONTRACT_MISMATCH", diagnostic: "Response was not valid JSON", cause: err });
      }
    }
  }

  if (!response.ok) {
    throw mapApiError({
      httpStatus: response.status,
      body: (json ?? undefined) as ApiErrorBody | undefined,
      diagnostic: `HTTP ${response.status} calling ${method} ${path}`,
    });
  }

  return { status: response.status, json, requestId: responseRequestId };
}
