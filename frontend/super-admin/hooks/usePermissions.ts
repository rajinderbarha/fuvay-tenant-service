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
 */
export function usePermissions() {
  const me = useApi<AdminUser>(useCallback(() => authApi.me(), []));
  const permissions: string[] | null = me.loading ? null : (me.data?.permissions ?? []);
  const has = (permission: string) => {
    if (permissions === null) return false; // fail closed while loading
    return permissions.includes("*") || permissions.includes(permission);
  };
  return { has, loading: me.loading, role: me.data?.role ?? null, permissions };
}
