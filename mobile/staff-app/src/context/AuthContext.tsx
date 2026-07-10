import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { authApi, clearSession, STORAGE_KEYS, type StaffUser } from "../lib/api";

interface AuthCtx {
  user:     StaffUser | null;
  loading:  boolean;
  login:    (phone:string, password:string) => Promise<void>;
  logout:   () => Promise<void>;
  error:    string | null;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user,    setUser]    = useState<StaffUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEYS.token).then(token => {
      if (token) authApi.me().then(setUser).catch(() => {}).finally(() => setLoading(false));
      else setLoading(false);
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

  return <Ctx.Provider value={{ user, loading, login, logout, error }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
