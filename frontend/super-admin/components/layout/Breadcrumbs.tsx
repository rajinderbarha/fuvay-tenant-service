/**
 * Sprint 34K — Breadcrumbs component for Super-Admin portal.
 *
 * Renders breadcrumb trail from ADMIN_PAGE_REGISTRY or explicit crumbs.
 * Usage:
 *   <Breadcrumbs pathname={pathname} />
 *   <Breadcrumbs crumbs={[{ label: "Catalog" }, { label: "Categories" }]} />
 */
"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { resolvePageMeta } from "../../lib/page-registry";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  crumbs?: BreadcrumbItem[];
  pathname?: string;
  className?: string;
}

export function Breadcrumbs({ crumbs, pathname, className }: BreadcrumbsProps) {
  const currentPath = usePathname();
  const path = pathname ?? currentPath;

  // Resolve crumbs from registry if not explicitly provided
  const resolved: BreadcrumbItem[] = crumbs ?? (() => {
    const meta = resolvePageMeta(path);
    return meta?.breadcrumbs ?? [{ label: "Admin", href: "/admin/dashboard" }];
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
        ...(className ? {} : {}),
      }}
    >
      {resolved.map((crumb, i) => {
        const isLast = i === resolved.length - 1;
        return (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            {i > 0 && <span style={{ color: "#d1d5db" }}>/</span>}
            {crumb.href && !isLast ? (
              <Link
                href={crumb.href}
                style={{
                  color: "#6b7280",
                  textDecoration: "none",
                  transition: "color 0.15s",
                }}
                onMouseEnter={e => { (e.target as HTMLAnchorElement).style.color = "#1e3a5f"; }}
                onMouseLeave={e => { (e.target as HTMLAnchorElement).style.color = "#6b7280"; }}
              >
                {crumb.label}
              </Link>
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
