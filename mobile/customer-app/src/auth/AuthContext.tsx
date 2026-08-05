import React, { createContext, useContext, useEffect, useState } from "react";
import { getSessionSnapshot, subscribeSessionSnapshot, SessionSnapshot } from "../api/session/sessionEvents";
import { restoreSession, logout as sessionLogout } from "../api/session/sessionManager";

/**
 * Phase F: this provider now mirrors the real session-manager state
 * (api/session/sessionManager.ts + sessionEvents.ts) instead of reading
 * secure storage directly -- it is a thin React subscription over the
 * single source of truth Phase E's navigation resolver also consumes
 * (see navigation/useNavigationSnapshot.ts), so both stay in sync without
 * either owning a second copy of "am I logged in."
 */
interface AuthContextValue extends SessionSnapshot {
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>(getSessionSnapshot());

  useEffect(() => {
    const unsubscribe = subscribeSessionSnapshot(setSnapshot);
    if (getSessionSnapshot().state === "uninitialized") {
      restoreSession().catch(() => {});
    }
    return unsubscribe;
  }, []);

  const value: AuthContextValue = { ...snapshot, signOut: sessionLogout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
