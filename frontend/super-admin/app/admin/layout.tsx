"use client";
/**
 * Next.js App Router route-level layout for all /admin/* pages.
 * Wraps every admin page with AdminLayout (sidebar + topbar).
 * Sprint 34K: nav mapping delegated to centralized nav-config.ts
 */
import { usePathname } from "next/navigation";
import { AdminLayout, resolveActiveNavId } from "../../components/layout/AdminLayout";

// ADMIN-TENANT-E2E-02 Part 3: previously delegated to lib/nav-config.ts's
// resolveAdminNavId(), a hand-maintained path-segment map that had drifted out
// of sync with AdminLayout's actual NAV_GROUPS (different ids, missing entries
// for sub-routes like /admin/users/roles or /admin/users/permissions, which
// both fell back to the parent "users" id). resolveActiveNavId() instead does
// longest-href-prefix matching directly against the sidebar's real hrefs, so
// nested routes always highlight the correct (most specific) sidebar item.
function pathToActiveNav(pathname: string): string {
  return resolveActiveNavId(pathname);
}

export default function AdminShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AdminLayout activeNav={pathToActiveNav(pathname)}>
      {children}
    </AdminLayout>
  );
}
