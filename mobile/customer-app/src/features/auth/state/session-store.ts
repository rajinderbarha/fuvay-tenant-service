import { secureStorage } from "../../../storage/secure-storage";
import { SECURE_STORAGE_KEYS } from "../../../storage/storage-keys";
import { setAuthTokenProvider } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { CustomerSession } from "../domain/session";

export type SessionStatus = "unknown" | "authenticated" | "guest";

interface SessionState {
  status: SessionStatus;
  session: CustomerSession | null;
}

let state: SessionState = { status: "unknown", session: null };
const listeners = new Set<(state: SessionState) => void>();

function setState(next: SessionState) {
  state = next;
  listeners.forEach((listener) => listener(state));
}

export function getSessionState(): SessionState {
  return state;
}

export function subscribeSession(listener: (state: SessionState) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Reads the persisted refresh token (never the access token alone — an
 * access token with no refresh token is useless once expired) and marks
 * the store "guest" if none exists. Does not itself call `/v1/auth/me` —
 * the caller (`useAuthSession`) does that once it has a token, so this
 * function stays a pure storage read with no network dependency.
 */
export async function hydrateSessionTokens(): Promise<{ accessToken: string; refreshToken: string } | null> {
  const [accessToken, refreshToken] = await Promise.all([
    secureStorage.getItem(SECURE_STORAGE_KEYS.accessToken),
    secureStorage.getItem(SECURE_STORAGE_KEYS.refreshToken),
  ]);
  if (!accessToken || !refreshToken) {
    setState({ status: "guest", session: null });
    return null;
  }
  return { accessToken, refreshToken };
}

export async function persistSession(session: CustomerSession): Promise<void> {
  const [accessWritten, refreshWritten] = await Promise.all([
    secureStorage.setItem(SECURE_STORAGE_KEYS.accessToken, session.accessToken),
    secureStorage.setItem(SECURE_STORAGE_KEYS.refreshToken, session.refreshToken),
  ]);
  // In-memory state still reflects "authenticated" even on a write failure —
  // the customer can keep using the app for this run — but a write failure
  // means the session will NOT survive an app restart, which is worth
  // knowing about rather than silently discovering it as a mystery logout.
  if (!accessWritten || !refreshWritten) {
    logger.warn("auth.session_persist_failed", { accessWritten, refreshWritten });
  }
  setState({ status: "authenticated", session });
  logger.info("auth.session_established", { userId: session.userId });
}

export async function clearSession(): Promise<void> {
  await Promise.all([secureStorage.removeItem(SECURE_STORAGE_KEYS.accessToken), secureStorage.removeItem(SECURE_STORAGE_KEYS.refreshToken)]);
  setState({ status: "guest", session: null });
  logger.info("auth.session_cleared");
}

export function updateSessionProfile(patch: Partial<CustomerSession>): void {
  if (!state.session) return;
  setState({ status: "authenticated", session: { ...state.session, ...patch } });
}

/**
 * Registers the store's access token with the API client
 * (CUSTOMER-L5-00's `api/request-context.ts#setAuthTokenProvider`) — the
 * client stays decoupled from how auth is implemented, only ever calling
 * this one function.
 */
export function bindSessionToApiClient(): void {
  setAuthTokenProvider(async () => getSessionState().session?.accessToken ?? null);
}

export function __resetSessionStoreForTests(): void {
  state = { status: "unknown", session: null };
  listeners.clear();
}
