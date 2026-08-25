/**
 * Sprint 34K — Breadcrumbs component for Tenant Portal.
 */
"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { resolveTenantPageMeta } from "../../lib/page-registry";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

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
        color: "var(--text-tertiary)",
        marginBottom: "0.75rem",
      }}
    >
      {resolved.map((crumb, i) => {
        const isLast = i === resolved.length - 1;
        return (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            {i > 0 && <span style={{ color: "var(--border-strong)" }}>/</span>}
            {crumb.href && !isLast ? (
              <Link
                href={crumb.href}
                style={{ color: "var(--text-secondary)", textDecoration: "none", transition: "color 0.15s" }}
                onMouseEnter={e => { e.currentTarget.style.color = "var(--text-link)"; }}
                onMouseLeave={e => { e.currentTarget.style.color = "var(--text-secondary)"; }}
              >
                {crumb.label}
              </Link>
            ) : (
              <span style={{ color: isLast ? "var(--text-primary)" : "var(--text-tertiary)", fontWeight: isLast ? 500 : 400 }}>
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
