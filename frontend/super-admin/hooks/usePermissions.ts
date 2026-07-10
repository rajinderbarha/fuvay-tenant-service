"use client";
import { useCallback } from "react";
import { authApi, type AdminUser } from "../lib/api";
import { useApi } from "./useApi";

export function usePermissions() {
  const me = useApi<AdminUser>(useCallback(() => authApi.me(), []));
  const perms = me.data?.permissions ?? [];
  const has = (permission: string) => perms.includes("*") || perms.includes(permission);
  return { has, loading: me.loading, role: me.data?.role ?? null };
}
