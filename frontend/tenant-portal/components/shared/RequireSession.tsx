"use client";
/**
 * Nothing inside the tenant portal renders until the SERVER confirms a session.
 *
 * The old check ran in a useEffect inside TenantLayout and asked only whether a
 * token string existed in localStorage. Both halves leaked:
 *
 *   an effect runs AFTER the first paint, so the page rendered, then
 *   redirected -- the provider saw their real data on the way out;
 *
 *   an expired token is still a string, so the check passed and every page
 *   rendered normally until some API call happened to 401.
 *
 * A page with no API call, or one showing already-fetched state, simply stayed
 * on screen. So the question here is not "is there a token" but "does the
 * server still accept it", and children are withheld until it answers.
 *
 * WHAT COUNTS AS AN ANSWER
 *   Only the server saying "not you" ends a session. The first version of this
 *   guard treated ANY rejected promise as "signed out", which meant a network
 *   blip, a 500, a restarting backend -- or simply clicking a link while the
 *   check was still in flight, which aborts the request -- silently logged out
 *   a perfectly valid user. That was caught in a browser test: `me()` rejected
 *   with "Failed to fetch" (an aborted request, not a 401) and this guard threw
 *   the session away.
 *
 *   So a failure that is not an authentication rejection is treated as "cannot
 *   tell", never as "not authenticated": the session is left intact, the check
 *   is retried, and content stays withheld in the meantime. Withholding is safe;
 *   destroying a valid session is not.
 */
import React, { useEffect, useState } from "react";

import { authApi, clearSession, ServiceOSError } from "../../lib/api";

type SessionState = "checking" | "authenticated" | "rejected" | "unavailable";

const TOKEN_KEY = "serviceos_tenant_token";
const MAX_RETRIES = 2;

/** The server refusing the token -- as opposed to never being reached at all.
 *  apiFetch raises this only after a 401 that a refresh could not rescue. */
function isAuthRejection(err: unknown): boolean {
  return err instanceof ServiceOSError && err.code === "UNAUTHORIZED";
}

export function RequireSession({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let leaving = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    // A navigation aborts in-flight requests. Without this, a provider who
    // clicks a link while the check is running gets signed out for it.
    const markLeaving = () => { leaving = true; };
    window.addEventListener("pagehide", markLeaving);
    window.addEventListener("beforeunload", markLeaving);

    const cleanup = () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      window.removeEventListener("pagehide", markLeaving);
      window.removeEventListener("beforeunload", markLeaving);
    };

    // No token at all: no point asking the server.
    if (!localStorage.getItem(TOKEN_KEY)) {
      setState("rejected");
      clearSession();
      return cleanup;
    }

    const check = (tries: number) => {
      authApi.me()
        .then(() => { if (!cancelled) setState("authenticated"); })
        .catch((err: unknown) => {
          if (cancelled || leaving) return;
          if (isAuthRejection(err)) {
            // Expired, revoked, or a user who no longer exists -- all the same
            // answer. apiFetch has already cleared and redirected on this path;
            // calling again is harmless and keeps the guard self-contained.
            setState("rejected");
            clearSession();
            return;
          }
          // Could not reach the server, or it failed for an unrelated reason.
          // The session may well still be good, so leave it alone.
          if (tries < MAX_RETRIES) {
            timer = setTimeout(() => check(tries + 1), 500 * (tries + 1));
            return;
          }
          setState("unavailable");
        });
    };
    // Let React Strict Mode clean up its throwaway effect before the network
    // request starts. Otherwise every route transition checks the same session
    // twice and one aborted request can win the state race.
    timer = setTimeout(() => check(0), 0);

    return cleanup;
  }, [attempt]);

  if (state === "authenticated") return <>{children}</>;

  if (state === "unavailable") {
    // Deliberately NOT a redirect: the token is probably still valid and the
    // provider should not lose their session because the network wobbled.
    return (
      <div role="status" style={{ minHeight: "60vh", display: "flex", alignItems: "center",
        justifyContent: "center", flexDirection: "column", gap: 12, textAlign: "center" }}>
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>
          Can&apos;t reach the server to confirm your session.
        </p>
        <button
          type="button"
          onClick={() => { setState("checking"); setAttempt(a => a + 1); }}
          style={{ padding: "8px 16px", borderRadius: 8, cursor: "pointer",
            border: "1px solid var(--border-default)", background: "var(--bg-surface)",
            color: "var(--text-primary)" }}
        >
          Try again
        </button>
      </div>
    );
  }

  // "checking" and "rejected" both render nothing: during the check because we
  // do not yet know, and after a rejection because the redirect is in flight
  // and showing the page in the meantime is the bug this fixes.
  return (
    <div
      aria-busy={state === "checking"}
      aria-label={state === "checking" ? "Checking your session" : "Signing you out"}
      style={{ minHeight: "60vh" }}
    />
  );
}
