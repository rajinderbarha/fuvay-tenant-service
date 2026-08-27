"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BreadcrumbTrail, type BreadcrumbTrailItem } from "@serviceos/design-system";
import { resolvePageMeta } from "../../lib/page-registry";

export type BreadcrumbItem = BreadcrumbTrailItem;

export function Breadcrumbs({
  crumbs,
  pathname,
  className,
}: {
  crumbs?: BreadcrumbItem[];
  pathname?: string;
  className?: string;
}) {
  const path = pathname ?? usePathname();
  if (path === "/admin/dashboard") return null;

  const source = crumbs ?? resolvePageMeta(path)?.breadcrumbs ?? [];
  const items = source[0]?.href === "/admin/dashboard"
    ? source
    : [{ label: "Admin", href: "/admin/dashboard" }, ...source];

  return <BreadcrumbTrail
    items={items}
    className={className}
    renderLink={(href, children) => (
      <Link href={href} style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
        {children}
      </Link>
    )}
  />;
}

export default Breadcrumbs;
