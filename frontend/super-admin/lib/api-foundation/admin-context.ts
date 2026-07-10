/**
 * FRONTEND-CONNECT-01 — Admin route/context helpers.
 * Admin pages authenticate as platform admin and do NOT require tenant
 * context unless viewing a specific tenant's detail (which takes an
 * explicit tenantId route param, never a fabricated/fallback one).
 */

/** True for any route under /admin (platform-admin auth, no tenant context needed). */
export function isAdminRoute(pathname: string): boolean {
  return pathname.startsWith("/admin");
}

export class AdminAccessDeniedError extends Error {
  constructor(public requestId?: string) {
    super(
      requestId
        ? `You do not have permission to perform this action. Request ID: ${requestId}`
        : "You do not have permission to perform this action.",
    );
    this.name = "AdminAccessDeniedError";
  }
}

/** Call after receiving a 403 from an admin-scoped call to raise a consistent error. */
export function requireAdminAccess(hasAccess: boolean, requestId?: string): void {
  if (!hasAccess) throw new AdminAccessDeniedError(requestId);
}
