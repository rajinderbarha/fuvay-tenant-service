import { useEffect, useState } from "react";
import { getSessionState, subscribeSession } from "../state/session-store";
import type { CustomerSession } from "../domain/session";

export interface UseAuthSessionResult {
  status: "unknown" | "authenticated" | "guest";
  session: CustomerSession | null;
}

/** The sanctioned way for screens to read the current session — never import session-store.ts directly from a screen. */
export function useAuthSession(): UseAuthSessionResult {
  const [state, setState] = useState(getSessionState());
  useEffect(() => subscribeSession(setState), []);
  return state;
}
