/**
 * FRONTEND-CONNECT-01 — Standard API Error Model (super-admin)
 *
 * Mirrors frontend/tenant-portal/lib/api-foundation/error-model.ts.
 * apiFetch() in ../api.ts continues to throw ServiceOSError unchanged
 * (touching every call site is out of scope) — toApiError() normalizes
 * ServiceOSError and any other thrown value into one ApiError shape
 * for the new shared error-state UI components.
 */
import { ServiceOSError } from "../api";

export type ApiError = {
  code: string;
  message: string;
  request_id?: string;
  status?: number;
  field_errors?: Record<string, string[]>;
  raw?: unknown;
};

export function toApiError(e: unknown, status?: number): ApiError {
  if (e instanceof ServiceOSError) {
    const fieldErrors = (e.context && typeof e.context === "object" && "field_errors" in e.context)
      ? (e.context as Record<string, unknown>).field_errors as Record<string, string[]>
      : undefined;
    return {
      code: e.code || "API_ERROR",
      message: e.message || "Unexpected error.",
      request_id: e.requestId,
      status,
      field_errors: fieldErrors,
      raw: e,
    };
  }
  if (e instanceof DOMException && e.name === "AbortError") {
    return { code: "TIMEOUT", message: "The request timed out. Please try again.", raw: e };
  }
  if (e instanceof TypeError) {
    return { code: "NETWORK_ERROR", message: "Could not reach the server. Check your connection and try again.", raw: e };
  }
  if (e instanceof Error) {
    return { code: "UNKNOWN_ERROR", message: e.message || "Something went wrong. Please try again.", raw: e };
  }
  if (typeof e === "string") {
    return { code: "UNKNOWN_ERROR", message: e, raw: e };
  }
  return { code: "UNKNOWN_ERROR", message: "Something went wrong. Please try again.", raw: e };
}

export async function parseErrorResponse(res: Response): Promise<ApiError> {
  const status = res.status;
  let body: unknown = null;
  try { body = await res.json(); } catch { /* not JSON */ }

  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (status === 401) return { code: "UNAUTHORIZED", message: "Session expired. Please login again.", status, request_id: b.request_id as string | undefined };
    if (status === 403) return {
      code: "FORBIDDEN",
      message: `You do not have permission to perform this action. Request ID: ${b.request_id ?? "unknown"}`,
      status, request_id: b.request_id as string | undefined,
    };
    if (status === 422) return {
      code: "VALIDATION_ERROR",
      message: (b.detail as string) ?? "Some fields are invalid.",
      status, request_id: b.request_id as string | undefined,
      field_errors: b.field_errors as Record<string, string[]> | undefined,
    };
    return {
      code: (b.error_code as string) ?? `HTTP_${status}`,
      message: (b.detail as string) ?? `Request failed with status ${status}.`,
      status, request_id: b.request_id as string | undefined,
      raw: body,
    };
  }
  let text = "";
  try { text = await res.clone().text(); } catch { /* already consumed */ }
  if (status === 401) return { code: "UNAUTHORIZED", message: "Session expired. Please login again.", status };
  if (status === 403) return { code: "FORBIDDEN", message: "You do not have permission to perform this action.", status };
  if (status === 404) return { code: "NOT_FOUND", message: "The requested resource was not found.", status };
  if (status >= 500) return { code: "SERVER_ERROR", message: "Something went wrong on our end. Please try again.", status };
  return { code: `HTTP_${status}`, message: text || `Request failed with status ${status}.`, status };
}
