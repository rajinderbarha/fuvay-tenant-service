import { ENV } from "../../config/environment";
import { ApiRequestOptions, ApiResult } from "./types";
import { safeParseJson, isSuccessEnvelope, isProblemDetail } from "./responseParser";
import { mapProblemDetail, mapNetworkFailure, mapUnknownFailure, ErrorMapperContext } from "./errorMapper";
import { getRetryDecision, sleep } from "./retryPolicy";
import { redactHeaders } from "../../utils/redaction";

/**
 * Shared low-level transport (Phase F spec section 4) -- publicClient and
 * authenticatedClient both call this; it owns timeout/abort/retry/error-
 * normalization so neither client (nor feature code) duplicates that logic.
 */
export interface RawRequestInput {
  path: string;
  headers: Record<string, string>;
  options: ApiRequestOptions;
  context: ErrorMapperContext;
}

function buildUrl(path: string, query?: ApiRequestOptions["query"]): string {
  const url = new URL(path.replace(/^\/?/, "/"), ENV.apiBaseUrl);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function performOnce<T>(input: RawRequestInput): Promise<ApiResult<T>> {
  const { path, headers, options, context } = input;
  const url = buildUrl(path, options.query);
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? ENV.apiTimeoutMs;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  // If the caller passed their own signal (screen/query disposal), abort
  // this request the moment either fires.
  const externalSignal = options.signal;
  const onExternalAbort = () => controller.abort();
  externalSignal?.addEventListener("abort", onExternalAbort);

  try {
    const response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
    const json = await safeParseJson(response);

    if (response.ok) {
      if (isSuccessEnvelope<T>(json)) {
        return { ok: true, data: json.data, meta: json.meta, links: json.links };
      }
      return { ok: false, error: mapUnknownFailure(response.status, undefined, json) };
    }

    if (isProblemDetail(json)) {
      return { ok: false, error: mapProblemDetail(json, context, response.headers.get("X-Request-ID") ?? undefined) };
    }
    return { ok: false, error: mapUnknownFailure(response.status, response.headers.get("X-Request-ID") ?? undefined, json) };
  } catch (err) {
    if (externalSignal?.aborted) {
      return { ok: false, error: mapNetworkFailure("abort") };
    }
    if (controller.signal.aborted) {
      // Our own timeout fired (external signal didn't) -- a genuine timeout.
      return { ok: false, error: mapNetworkFailure("timeout") };
    }
    return { ok: false, error: mapNetworkFailure("offline", undefined) };
  } finally {
    clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}

/**
 * Performs the request with bounded retry for transient/idempotent-safe
 * failures. `unsafeToRetry` (set by mutation call sites that aren't
 * idempotency-key protected) disables all automatic retry regardless of
 * error classification.
 */
export async function performRequest<T>(input: RawRequestInput): Promise<ApiResult<T>> {
  let attempt = 0;
  // Loud, not silent, about a misconfigured production/staging domain: this
  // never executes on `local`, purely a development-time safety net.
  while (true) {
    attempt += 1;
    const result = await performOnce<T>(input);
    if (result.ok) return result;

    const decision = getRetryDecision(result.error, attempt, !!input.options.unsafeToRetry);
    if (!decision.shouldRetry) {
      if (__DEV__ && result.error.category !== "cancelled") {
        // Redacted diagnostic only -- never the raw headers/body.
        // eslint-disable-next-line no-console
        console.warn("[api]", input.path, result.error.code, redactHeaders(input.headers));
      }
      return result;
    }
    await sleep(decision.delayMs);
  }
}
