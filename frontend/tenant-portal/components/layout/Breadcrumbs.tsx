/**
 * Sprint 34K — Breadcrumbs component for Tenant Portal.
 *
 * Phase 2A Slice 2B: added an optional context-based override so a
 * contextual detail page (e.g. a specific ServiceJob) can inject its real
 * entity name ("Job SJ-2049") into the breadcrumb trail, reconstructing
 * correct deep-link context — without every such page needing its own
 * layout wrapper. TenantLayout renders <Breadcrumbs/> automatically via
 * app/(tenant)/layout.tsx, so a page several levels below it has no direct
 * prop channel; this context is that channel, mirroring the existing
 * AdminMenuRefreshCtx pattern already used in the super-admin app for the
 * same "page needs to talk up to its auto-mounted shell" problem.
 */
"use client";

import { createContext, useContext, useEffect } from "react";
import { usePathname } from "next/navigation";
import { resolveTenantPageMeta } from "../../lib/page-registry";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

const BreadcrumbOverrideCtx = createContext<(crumbs: BreadcrumbItem[] | null) => void>(() => {});

/** Call from a contextual detail page (inside TenantLayout's children) to
 * override the auto-resolved breadcrumb with one that includes the real
 * record — e.g. `useBreadcrumbOverride(job ? [{label:"Jobs",href:"/jobs"},
 * {label:"Service Job "+job.job_number}] : null)`. Pass `null` to fall back
 * to the static page-registry resolution (e.g. while the record is still
 * loading, rather than showing a wrong or empty trail). */
export function useBreadcrumbOverride(crumbs: BreadcrumbItem[] | null) {
  const setOverride = useContext(BreadcrumbOverrideCtx);
  const key = crumbs ? JSON.stringify(crumbs) : null;
  useEffect(() => {
    setOverride(crumbs);
    return () => setOverride(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}

export { BreadcrumbOverrideCtx };

interface BreadcrumbsProps {
  crumbs?: BreadcrumbItem[];
  pathname?: string;
}

export function Breadcrumbs({ crumbs, pathname }: BreadcrumbsProps) {
  const currentPath = usePathname();
  const path = pathname ?? currentPath;

  const resolved: BreadcrumbItem[] = crumbs ?? (() => {
    const meta = resolveTenantPageMeta(path);
    return meta?.breadcrumbs ?? [{ label: "Dashboard", href: "/dashboard" }];
  })();

  if (resolved.length <= 1) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.375rem",
        fontSize: "0.78rem",
        color: "#9ca3af",
        marginBottom: "0.75rem",
      }}
    >
      {resolved.map((crumb, i) => {
        const isLast = i === resolved.length - 1;
        return (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            {i > 0 && <span style={{ color: "#d1d5db" }}>/</span>}
            {crumb.href && !isLast ? (
              <a
                href={crumb.href}
                style={{ color: "#6b7280", textDecoration: "none" }}
              >
                {crumb.label}
              </a>
            ) : (
              <span style={{ color: isLast ? "#374151" : "#9ca3af", fontWeight: isLast ? 500 : 400 }}>
                {crumb.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export default Breadcrumbs;
