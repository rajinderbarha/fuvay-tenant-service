import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { authApi, clearSession, ServiceOSError, STORAGE_KEYS, type StaffUser } from "../lib/api";

interface AuthCtx {
  user:     StaffUser | null;
  loading:  boolean;
  login:    (phone:string, password:string) => Promise<void>;
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

  async function login(phone: string, password: string) {
    setError(null);
    try {
      const { access_token, staff } = await authApi.login(phone, password);
      await AsyncStorage.multiSet([
        [STORAGE_KEYS.token,    access_token],
        [STORAGE_KEYS.staffId,  staff.id],
        [STORAGE_KEYS.name,     staff.full_name],
        [STORAGE_KEYS.phone,    staff.phone ?? ""],
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
