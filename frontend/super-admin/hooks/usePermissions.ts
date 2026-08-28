"use client";
import { useCallback } from "react";
import { authApi, type AdminUser } from "../lib/api";
import { useApi } from "./useApi";

/**
 * FINAL-L5-05M: the one shared source of effective-permission state for
 * every consumer (AdminLayout sidebar, route guards, action guards). Always
 * backed by the server-provided GET /v1/auth/me payload — never computed
 * client-side. `permissions` is `null` while the fetch is in flight or has
 * not yet started, distinct from `[]` (a real, resolved "no permissions"
 * result) so callers can fail closed during loading without permanently
 * treating "still loading" as "denied forever".
 *
 * `authenticated` is a THIRD state, and the reason this hook is not just
 * `permissions`. When the token has expired, /auth/me fails: `loading` goes
 * false and `data` is null, which used to collapse to `permissions = []` --
 * indistinguishable from a real user who happens to hold no permissions. Any
 * route whose requirement is "" (the Dashboard, self-service pages) then
 * rendered its content to someone holding an expired token, because "no
 * permission required" was being read as "no session required".
 *
 * So: `authenticated === false` means the server did not confirm a session,
 * and no route may render regardless of what it requires.
 */
export function usePermissions() {
  const me = useApi<AdminUser>(useCallback(() => authApi.me(), []));

  // Resolved and confirmed by the server, or not resolved at all.
  const authenticated: boolean | null = me.loading ? null : Boolean(me.data && !me.error);
  const permissions: string[] | null =
    me.loading || !authenticated ? null : (me.data?.permissions ?? []);

  const has = (permission: string) => {
    if (permissions === null) return false; // fail closed while loading or unauthenticated
    return permissions.includes("*") || permissions.includes(permission);
  };

  return {
    has,
    loading: me.loading,
    authenticated,
    role: me.data?.role ?? null,
    permissions,
  };
}
