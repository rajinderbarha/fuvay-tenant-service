import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { authApi, clearSession, ServiceOSError, STORAGE_KEYS, type StaffUser } from "../lib/api";

interface AuthCtx {
  user:     StaffUser | null;
  loading:  boolean;
  login:    (email:string, password:string) => Promise<void>;
  logout:   () => Promise<void>;
  error:    string | null;
  // UX-05 Round 7: real session-expiry signal, driven by an actual 401 from
  // the backend on the initial /me check (a stored token that the backend
  // no longer accepts) -- not a fabricated/timer-based expiry. Distinct
  // from `error` (a login-attempt failure) -- this fires on APP START with
  // a stale token, before any login attempt happens.
  sessionExpired: boolean;
  clearSessionExpired: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user,    setUser]    = useState<StaffUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEYS.token).then(token => {
      if (!token) { setLoading(false); return; }
      authApi.me()
        .then(setUser)
        .catch(async (e: unknown) => {
          // A real 401 here means the stored token exists but the backend
          // rejects it (expired/revoked) -- distinct from a network error
          // or a 5xx, which we don't want to mislabel as "session expired."
          if (e instanceof ServiceOSError && e.status === 401) {
            setSessionExpired(true);
            await clearSession();
          }
        })
        .finally(() => setLoading(false));
    });
  }, []);

  async function login(email: string, password: string) {
    setError(null);
    try {
      // UX-05B FIX 1: real /v1/auth/login response is {access_token,
      // refresh_token, user:{id,email,full_name,role,tenant_id,phone,...}},
      // not {access_token, staff:StaffUser}. specialisations/status/rating
      // aren't returned by this endpoint (they never were on /v1/auth/*) --
      // defaulted here the same way the pre-existing /v1/auth/me path did.
      const { access_token, user: authUser } = await authApi.login(email, password);
      const staff: StaffUser = {
        id: authUser.id, full_name: authUser.full_name,
        phone: authUser.phone ?? undefined, email: authUser.email,
        specialisations: [], status: authUser.is_active ? "active" : "inactive",
        tenant_id: authUser.tenant_id ?? undefined,
      };
      await AsyncStorage.multiSet([
        [STORAGE_KEYS.token,    access_token],
        [STORAGE_KEYS.staffId,  staff.id],
        [STORAGE_KEYS.name,     staff.full_name],
        [STORAGE_KEYS.tenantId, staff.tenant_id ?? ""],
      ]);
      setUser(staff);
      setSessionExpired(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed.");
      throw e;
    }
  }

  async function logout() {
    try { await authApi.logout(); } catch { /* ignore */ }
    await clearSession();
    setUser(null);
  }

  function clearSessionExpired() { setSessionExpired(false); }

  return <Ctx.Provider value={{ user, loading, login, logout, error, sessionExpired, clearSessionExpired }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
