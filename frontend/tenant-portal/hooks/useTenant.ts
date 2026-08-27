"use client";
import { useState, useEffect } from "react";
import { categoryDashboardApi, ServiceOSError } from "../lib/api";

export interface TenantContext {
  tenantId: string | null; tenantName: string | null; vertical: string | null;
  city: string | null; healthScore: number | null; userId: string | null;
  categoryName: string | null; categorySlug: string | null;
  loading: boolean; error: string | null; requestId: string | null;
}

export function useTenant(): TenantContext {
  const [ctx, setCtx] = useState<TenantContext>({
    tenantId: null, tenantName: null, vertical: null, city: null,
    healthScore: null, userId: null, categoryName: null, categorySlug: null,
    loading: true, error: null, requestId: null,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const cachedVertical = localStorage.getItem("serviceos_tenant_vertical");
    setCtx(prev => ({
      ...prev,
      tenantId: localStorage.getItem("serviceos_tenant_id"),
      tenantName: localStorage.getItem("serviceos_tenant_name"),
      vertical: cachedVertical,
      city: localStorage.getItem("serviceos_tenant_city"),
      healthScore: Number(localStorage.getItem("serviceos_tenant_health") || 0) || null,
      userId: localStorage.getItem("serviceos_user_id"),
      // A cached vertical lets dependent pages paint immediately; if it's
      // missing we stay in `loading` until the live refresh below resolves,
      // rather than falsely reporting a non-Home-Services tenant.
      loading: !cachedVertical,
    }));

    // Self-heal: always refresh from the live backend runtime, regardless of
    // cache state. A stale/blank cached vertical (e.g. left over from before
    // a backend fix, or a tenant whose category changed since last login)
    // must never permanently block a Home-Services-only guard — this is the
    // root cause of the "Demo AC Services shows blocked" bug: the value was
    // only ever set once at login and never re-verified against the server.
    categoryDashboardApi.getRuntime()
      .then(rt => {
        const vertical = rt.category_type
          ?? rt.category?.category_type
          ?? rt.tenant?.category?.category_type
          ?? null;
        const categoryName = rt.category?.name ?? rt.tenant?.category?.name ?? null;
        const categorySlug = rt.category?.slug ?? rt.tenant?.category?.slug ?? null;

        if (vertical) localStorage.setItem("serviceos_tenant_vertical", vertical);
        if (rt.tenant?.business_name) localStorage.setItem("serviceos_tenant_name", rt.tenant.business_name);

        setCtx(prev => ({
          ...prev,
          vertical: vertical ?? prev.vertical,
          categoryName, categorySlug,
          tenantName: rt.tenant?.business_name ?? prev.tenantName,
          loading: false, error: null, requestId: null,
        }));
      })
      .catch((e: unknown) => {
        setCtx(prev => ({
          ...prev,
          loading: false,
          error: e instanceof ServiceOSError ? e.message : "Could not load tenant context.",
          requestId: e instanceof ServiceOSError ? (e.requestId ?? null) : null,
        }));
      });
  }, []);

  return ctx;
}
