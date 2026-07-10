/** Customer auth — uses the REAL shared /v1/auth/login endpoint (app/engines/auth/router.py).
 *  Verified live: a seeded user with role="customer" (customer@serviceos.in) logs in
 *  through this same endpoint as tenant/provider users; the JWT audience is
 *  "serviceos:customer" and role="customer". No separate customer-only auth
 *  endpoint exists, so this app reuses the generic one exactly like tenant-portal does. */
import { apiFetch, clearCustomerSession } from "./client";

export interface LoginResult {
  access_token: string;
  refresh_token?: string;
  user?: { id?: string; user_id?: string; full_name?: string; email?: string };
}

export async function customerLogin(email: string, password: string): Promise<LoginResult> {
  const res = await apiFetch<LoginResult>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  }, true);

  localStorage.setItem("serviceos_customer_token", res.access_token);
  if (res.refresh_token) localStorage.setItem("serviceos_customer_refresh", res.refresh_token);
  const u = res.user;
  localStorage.setItem("serviceos_customer_id", u?.id ?? u?.user_id ?? "");
  localStorage.setItem("serviceos_customer_name", u?.full_name ?? "");
  return res;
}

export function customerLogout() {
  clearCustomerSession();
  if (typeof window !== "undefined") window.location.href = "/login";
}
