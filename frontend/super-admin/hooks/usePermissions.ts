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
 * `authenticated` is deliberately THREE-valued, not two:
 *
 *   true   the server confirmed the session
 *   false  the server REFUSED it -- the only state that ends a session
 *   null   we cannot tell: still loading, or the request failed for a reason
 *          that says nothing about the token (network down, 500, a restarting
 *          backend, or a request aborted because the admin clicked a link)
 *
 * Collapsing that third case into `false` signs valid admins out over a
 * transient blip. Withholding content while unsure is safe; destroying a live
 * session is not. `unreachable` lets the gate show "try again" instead of
 * spinning forever in the null state.
 */
export function usePermissions() {
  const me = useApi<AdminUser>(useCallback(() => authApi.me(), []));

  // Only an explicit refusal from the server counts as "not signed in".
  const refused = me.errorCode === "UNAUTHORIZED";
  const authenticated: boolean | null =
    me.loading ? null
    : me.data   ? true
    : refused   ? false
    : null; // reached a verdict about nothing -- leave the session alone

  const unreachable = !me.loading && !me.data && !refused && me.error !== null;

  const permissions: string[] | null =
    authenticated === true ? (me.data?.permissions ?? []) : null;

  const has = (permission: string) => {
    if (permissions === null) return false; // fail closed while loading or unauthenticated
    return permissions.includes("*") || permissions.includes(permission);
  };

  return {
    has,
    loading: me.loading,
    authenticated,
    unreachable,
    retry: me.refetch,
    role: me.data?.role ?? null,
    permissions,
  };
}
