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
 */
import React, { useEffect, useState } from "react";

import { authApi, clearSession } from "../../lib/api";

type SessionState = "checking" | "authenticated" | "rejected";

export function RequireSession({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>("checking");

  useEffect(() => {
    let cancelled = false;

    // No token at all: no point asking the server.
    if (typeof window !== "undefined"
        && !localStorage.getItem("serviceos_tenant_token")) {
      setState("rejected");
      clearSession();
      return;
    }

    authApi.me()
      .then(() => { if (!cancelled) setState("authenticated"); })
      .catch(() => {
        if (cancelled) return;
        // Expired, revoked, or a user who no longer exists -- all the same
        // answer. clearSession() drops every session key and redirects; it is
        // idempotent, so a burst of failing calls still redirects once.
        setState("rejected");
        clearSession();
      });

    return () => { cancelled = true; };
  }, []);

  // "checking" and "rejected" both render nothing: during the check because we
  // do not yet know, and after a rejection because the redirect is in flight
  // and showing the page in the meantime is the bug this fixes.
  if (state !== "authenticated") {
    return (
      <div
        aria-busy={state === "checking"}
        aria-label={state === "checking" ? "Checking your session" : "Signing you out"}
        style={{ minHeight: "60vh" }}
      />
    );
  }

  return <>{children}</>;
}
