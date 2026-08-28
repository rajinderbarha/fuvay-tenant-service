"use client";
/**
 * Next.js App Router route-level layout for all /(tenant)/* pages.
 * Wraps every tenant page with TenantLayout (sidebar + topbar).
 * Sprint 34K: nav mapping delegated to centralized nav-config.ts
 */
import { usePathname } from "next/navigation";
import { TenantLayout } from "../../components/layout/TenantLayout";
import { RequireSession } from "../../components/shared/RequireSession";
import { resolveTenantNavId } from "../../lib/nav-config";

// Sprint 34K: use centralized nav-config resolver
function pathToActiveNav(pathname: string): string {
  return resolveTenantNavId(pathname);
}

export default function TenantShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    // RequireSession wraps the CHILDREN rather than the whole shell: the
    // sidebar may paint, but no page content is rendered until the server has
    // confirmed the session. Guarding here covers every /(tenant)/* route at
    // once, current and future, the way the admin portal guards its own.
    <TenantLayout activeNav={pathToActiveNav(pathname)}>
      <RequireSession>{children}</RequireSession>
    </TenantLayout>
  );
}
