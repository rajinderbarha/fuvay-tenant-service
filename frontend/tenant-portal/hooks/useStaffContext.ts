"use client";
import { useEffect, useState, useCallback } from "react";
import { authApi, getToken, type TenantUser } from "../lib/api";

export interface StaffContext {
  loading: boolean;
  user: TenantUser | null;
  isTechnician: boolean;
  error: string | null;
}

/** Loads the logged-in user and confirms they hold a staff/technician role.
 * Never trusts localStorage alone for the role gate — always re-verifies
 * against a live /v1/auth/me call so a stale/tampered localStorage value
 * can't grant access to pages meant for a different role. */
export function useStaffContext(): StaffContext {
  const [state, setState] = useState<StaffContext>({ loading: true, user: null, isTechnician: false, error: null });

  const load = useCallback(async () => {
    if (!getToken()) {
      setState({ loading: false, user: null, isTechnician: false, error: "Not logged in." });
      return;
    }
    try {
      const user = await authApi.me();
      const isTechnician = user.role === "technician" || user.role === "staff";
      setState({ loading: false, user, isTechnician, error: null });
    } catch (e) {
      setState({ loading: false, user: null, isTechnician: false, error: e instanceof Error ? e.message : "Failed to load staff context." });
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return state;
}
