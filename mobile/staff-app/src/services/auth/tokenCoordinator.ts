/**
 * In-memory token holder + session generation counter (Phase F spec
 * sections 6, 9). Raw token values live ONLY here and in SecureStore --
 * never in React context/state/selectors/component props (session state
 * exposes booleans like `accessTokenPresent`, never the token itself).
 *
 * `sessionGeneration` increments on establish/clear/revoke so a response
 * that arrives after a logout/account-switch (started under an earlier
 * generation) can be recognized as stale and discarded by
 * authenticatedClient, never written into whatever is now the active
 * session.
 */
let accessToken: string | null = null;
let refreshToken: string | null = null;
let sessionId: string | null = null;
let sessionGeneration = 0;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function getSessionId(): string | null {
  return sessionId;
}

export function getSessionGeneration(): number {
  return sessionGeneration;
}

export function isTokenPresent(): boolean {
  return accessToken !== null;
}

/** Sets tokens without bumping generation -- used for an in-place refresh
 * rotation where the session continues (not a new/cleared session). */
export function setTokens(next: { accessToken: string; refreshToken: string; sessionId?: string | null }): void {
  accessToken = next.accessToken;
  refreshToken = next.refreshToken;
  if (next.sessionId !== undefined) sessionId = next.sessionId;
}

/** Establishes a brand-new session generation (login, or first restore). */
export function establishTokens(next: { accessToken: string; refreshToken: string; sessionId: string | null }): void {
  accessToken = next.accessToken;
  refreshToken = next.refreshToken;
  sessionId = next.sessionId;
  sessionGeneration += 1;
}

/** Clears everything and bumps generation so in-flight requests from the
 * old session can never write into the next one. */
export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  sessionId = null;
  sessionGeneration += 1;
}

/** Test-only reset (generation resets to 0, unlike clearTokens). */
export function __resetTokenCoordinatorForTests(): void {
  accessToken = null;
  refreshToken = null;
  sessionId = null;
  sessionGeneration = 0;
}
