"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, getToken, type TenantUser } from "../lib/api";
import { authTimeline } from "../lib/authTimeline";

export interface StaffContext {
  loading: boolean;
  user: TenantUser | null;
  isTechnician: boolean;
  error: string | null;
}

/** Loads the logged-in user and confirms they hold a staff/technician role.
 * Never trusts localStorage alone for the role gate — always re-verifies
 * against a live /v1/auth/me call so a stale/tampered localStorage value
 * can't grant access to pages meant for a different role.
 *
 * This is the ONE place that should call authApi.me() for the staff app.
 * StaffLayout owns the single instance and shares it via StaffContextProvider
 * below — pages consume it with useStaffContextValue() instead of calling
 * this hook a second time, which would fire a second concurrent /v1/auth/me
 * request on every staff page load. */
export function useStaffContext(): StaffContext {
  const [state, setState] = useState<StaffContext>({ loading: true, user: null, isTechnician: false, error: null });

  const load = useCallback(async () => {
    authTimeline("staffContext.load_start");
    if (!getToken()) {
      authTimeline("staffContext.no_token");
      setState({ loading: false, user: null, isTechnician: false, error: "Not logged in." });
      return;
    }
    try {
      authTimeline("staffContext.me_request_start");
      const user = await authApi.me();
      authTimeline("staffContext.me_request_ok", user.role);
      const isTechnician = user.role === "technician" || user.role === "staff";
      setState({ loading: false, user, isTechnician, error: null });
    } catch (e) {
      authTimeline("staffContext.me_request_failed", e instanceof Error ? e.message : String(e));
      setState({ loading: false, user: null, isTechnician: false, error: e instanceof Error ? e.message : "Failed to load staff context." });
    }
  }, []);

  useEffect(() => { authTimeline("staffContext.hook_mounted"); load(); }, [load]);
  return state;
}

const StaffContextCtx = createContext<StaffContext | null>(null);
export const StaffContextProvider = StaffContextCtx.Provider;

/** Consumes the single StaffContext instance provided by StaffLayout.
 * Only valid inside <StaffLayout>'s children (i.e. after loading/auth
 * gating has already resolved) — throws early if misused so a missing
 * provider fails loudly instead of silently re-fetching. */
export function useStaffContextValue(): StaffContext {
  const ctx = useContext(StaffContextCtx);
  if (!ctx) throw new Error("useStaffContextValue() must be used within <StaffLayout>.");
  return ctx;
}
