/**
 * ServiceOS Customer App — Core API Client.
 * Mirrors frontend/tenant-portal/lib/api.ts conventions:
 *  - single apiFetch<T>() wrapper, no inline fetch() in components
 *  - auth token injected centrally, stored under serviceos_customer_* keys
 *  - every error normalized to CustomerApiError with request_id preserved
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class CustomerApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public requestId?: string,
    public status?: number,
    public context?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "CustomerApiError";
  }
}

export function getCustomerToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("serviceos_customer_token") : null;
}
export function getCustomerRefreshToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("serviceos_customer_refresh") : null;
}
export function getCustomerId(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("serviceos_customer_id") : null;
}
export function getCustomerName(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("serviceos_customer_name") : null;
}
export function isLoggedIn(): boolean {
  return !!getCustomerToken();
}
export function clearCustomerSession() {
  if (typeof window === "undefined") return;
  ["serviceos_customer_token", "serviceos_customer_refresh", "serviceos_customer_id", "serviceos_customer_name"]
    .forEach((k) => localStorage.removeItem(k));
}

function friendlyGenericMessage(requestId?: string): string {
  return `We couldn't complete this action. Please try again or contact support with this request ID. Request ID: ${requestId ?? "unknown"}`;
}

/** Parse ServiceOS's RFC7807-style error envelope (error_code/detail/request_id)
 *  AND the {"error":{code,message,request_id}} shape used by some endpoints. */
async function parseError(res: Response): Promise<CustomerApiError> {
  let body: any = null;
  try { body = await res.json(); } catch { /* not JSON */ }

  if (body?.error && typeof body.error === "object") {
    const e = body.error;
    return new CustomerApiError(e.code ?? `HTTP_${res.status}`, e.message ?? friendlyGenericMessage(e.request_id), e.request_id, res.status, e);
  }
  if (body && typeof body === "object") {
    const requestId = body.request_id;
    const code = body.error_code ?? `HTTP_${res.status}`;
    const message = body.detail ?? friendlyGenericMessage(requestId);
    return new CustomerApiError(code, message, requestId, res.status, body);
  }
  return new CustomerApiError(`HTTP_${res.status}`, friendlyGenericMessage(undefined), undefined, res.status);
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, skipAuth = false): Promise<T> {
  const token = getCustomerToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-Source": "customer-app",
    ...(options.headers as Record<string, string>),
  };
  if (token && !skipAuth) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !skipAuth) {
    const rt = getCustomerRefreshToken();
    if (rt) {
      try {
        const refreshRes = await fetch(`${API_BASE}/v1/auth/token/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (refreshRes.ok) {
          const j = await refreshRes.json();
          const newToken = j.data?.access_token ?? j.access_token;
          if (newToken) {
            localStorage.setItem("serviceos_customer_token", newToken);
            const retry = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...headers, Authorization: `Bearer ${newToken}` } });
            if (retry.ok) { const rj = await retry.json(); return rj.data as T; }
          }
        }
      } catch { /* fall through to logout */ }
    }
    clearCustomerSession();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new CustomerApiError("UNAUTHORIZED", "Session expired. Please sign in again.");
  }

  if (!res.ok) throw await parseError(res);

  const json = await res.json();
  return json.data as T;
}

export { API_BASE, friendlyGenericMessage };
