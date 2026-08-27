"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BreadcrumbTrail, type BreadcrumbTrailItem } from "@serviceos/design-system";
import { resolveTenantPageMeta } from "../../lib/page-registry";

export type BreadcrumbItem = BreadcrumbTrailItem;

export function Breadcrumbs({
  crumbs,
  pathname,
}: {
  crumbs?: BreadcrumbItem[];
  pathname?: string;
}) {
  const path = pathname ?? usePathname();
  if (path === "/dashboard") return null;

  const source = crumbs ?? resolveTenantPageMeta(path)?.breadcrumbs ?? [];
  const items = source[0]?.href === "/dashboard"
    ? source
    : [{ label: "Workspace", href: "/dashboard" }, ...source];

  return <BreadcrumbTrail
    items={items}
    renderLink={(href, children) => (
      <Link href={href} style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
        {children}
      </Link>
    )}
  />;
}

export default Breadcrumbs;
