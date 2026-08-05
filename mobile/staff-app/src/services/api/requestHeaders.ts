import { generateCorrelationId } from "./correlation";
import { RequestConcurrencyContract } from "./types";

/**
 * The ONLY place an Authorization header is constructed (Phase F spec
 * section 4: "Do not allow feature code to manually construct Authorization
 * headers"). Header names match real backend conventions: `X-Request-ID`
 * (app/middleware.py RequestIDMiddleware), `X-Idempotency-Key`
 * (app/core/idempotency.py).
 */
export function buildPublicHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-Request-ID": generateCorrelationId(),
    // No-op against the real backend; only matters when EXPO_PUBLIC_API_BASE_URL
    // points at a free ngrok tunnel (local dev over a physical device) -- ngrok's
    // free tier otherwise serves an HTML interstitial to any request whose
    // User-Agent looks browser-like (which React Native's fetch does), breaking
    // every API call with an unparseable-response error instead of JSON.
    "ngrok-skip-browser-warning": "true",
    ...extra,
  };
}

export function buildAuthenticatedHeaders(
  accessToken: string,
  idempotencyKey?: string,
  extra?: Record<string, string>,
): Record<string, string> {
  const headers = buildPublicHeaders(extra);
  headers.Authorization = `Bearer ${accessToken}`;
  if (idempotencyKey) headers["X-Idempotency-Key"] = idempotencyKey;
  return headers;
}

/**
 * The real backend concurrency convention is a BODY field, not a header --
 * confirmed in app/engines/invoice_payment/direct_payments_service.py
 * (`expected_version`) and app/engines/tenant_engine/workspace_settings_service.py
 * (`expected_version`). Future mutations merge their concurrency contract
 * into the JSON body via this helper rather than inventing header names.
 */
export function withConcurrencyFields<T extends Record<string, unknown>>(
  body: T,
  concurrency?: RequestConcurrencyContract,
): T & { expected_version?: number; quote_id?: string } {
  if (!concurrency) return body;
  const merged: Record<string, unknown> = { ...body };
  if (concurrency.entityVersion !== undefined) merged.expected_version = concurrency.entityVersion;
  if (concurrency.workflowVersion !== undefined) merged.expected_version = concurrency.workflowVersion;
  if (concurrency.quoteVersion !== undefined) merged.expected_version = concurrency.quoteVersion;
  if (concurrency.quoteId) merged.quote_id = concurrency.quoteId;
  return merged as T & { expected_version?: number; quote_id?: string };
}
