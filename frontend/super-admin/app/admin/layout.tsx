"use client";
/**
 * Next.js App Router route-level layout for all /admin/* pages.
 * Wraps every admin page with AdminLayout (sidebar + topbar).
 * Sprint 34K: nav mapping delegated to centralized nav-config.ts
 */
import { usePathname } from "next/navigation";
import { AdminLayout, resolveActiveNavId, getRequiredPermissionForRoute } from "../../components/layout/AdminLayout";
import { RequirePermission } from "../../components/shared/PermissionGate";

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
  const fullWidth = pathname.startsWith("/admin/home-services/service-jobs/");
  // FINAL-L5-05N: single root-level enforcement point covering every
  // /admin/* route (current and future) via nav-item permission
  // inheritance -- see getRequiredPermissionForRoute in AdminLayout.tsx.
  // Individual pages may still nest their own RequirePermission for a
  // more specific permission than their inherited nav-item default; the
  // root guard is the floor every route gets for free.
  return (
    <AdminLayout activeNav={pathToActiveNav(pathname)} fullWidth={fullWidth}>
      <RequirePermission requiredPermission={getRequiredPermissionForRoute(pathname)} parentLabel="Dashboard">
        {children}
      </RequirePermission>
    </AdminLayout>
  );
}
