import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { authApi, clearSession, STORAGE_KEYS, type CustomerUser } from "../lib/api";

interface AuthCtx {
  user:     CustomerUser | null;
  loading:  boolean;
  loginOtp: (phone:string, otp:string, sessionId:string) => Promise<void>;
  loginEmail:(email:string, password:string) => Promise<void>;
  logout:   () => Promise<void>;
  error:    string | null;
  clearError:()=>void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children:React.ReactNode }) {
  const [user,    setUser]    = useState<CustomerUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEYS.token).then(tok => {
      if (tok) authApi.me().then(setUser).catch(()=>{}).finally(()=>setLoading(false));
      else setLoading(false);
    });
  }, []);

  async function persist(token:string, customer:CustomerUser) {
    await AsyncStorage.multiSet([
      [STORAGE_KEYS.token,      token],
      [STORAGE_KEYS.customerId, customer.id],
      [STORAGE_KEYS.name,       customer.name],
      [STORAGE_KEYS.phone,      customer.phone ?? ""],
      [STORAGE_KEYS.email,      customer.email ?? ""],
    ]);
    setUser(customer);
  }

  async function loginOtp(phone:string, otp:string, sessionId:string) {
    setError(null);
    try {
      const { access_token, customer } = await authApi.verifyOtp(phone, otp, sessionId);
      await persist(access_token, customer);
    } catch(e:unknown) { setError(e instanceof Error ? e.message : "OTP verification failed."); throw e; }
  }

  async function loginEmail(email:string, password:string) {
    setError(null);
    try {
      const { access_token, customer } = await authApi.loginEmail(email, password);
      await persist(access_token, customer);
    } catch(e:unknown) { setError(e instanceof Error ? e.message : "Login failed."); throw e; }
  }

  async function logout() {
    try { await authApi.logout(); } catch { /**/ }
    await clearSession(); setUser(null);
  }

  return (
    <Ctx.Provider value={{ user, loading, loginOtp, loginEmail, logout, error, clearError:()=>setError(null) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
