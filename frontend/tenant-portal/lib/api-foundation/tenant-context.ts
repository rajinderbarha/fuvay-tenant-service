/**
 * FRONTEND-CONNECT-01 — Tenant context helpers.
 * Wraps the existing getTenantId() (lib/api.ts) with explicit
 * presence-checking so pages never silently call backend APIs with a
 * missing/undefined tenant_id.
 */
import { getTenantId } from "../api";

export interface TenantContext {
  tenantId: string;
}

/** Returns the tenant context, or null if not present. Never fabricates an id. */
export function getTenantContext(): TenantContext | null {
  const tenantId = getTenantId();
  if (!tenantId) return null;
  return { tenantId };
}

export class TenantContextMissingError extends Error {
  constructor(public requestId?: string) {
    super(
      requestId
        ? `Tenant context missing. Please select a business or login again. Request ID: ${requestId}`
        : "Tenant context missing. Please select a business or login again.",
    );
    this.name = "TenantContextMissingError";
  }
}

/** Throws TenantContextMissingError if no tenant context is present. */
export function requireTenantContext(requestId?: string): TenantContext {
  const ctx = getTenantContext();
  if (!ctx) throw new TenantContextMissingError(requestId);
  return ctx;
}

/** Runs `fn` only if tenant context is present; otherwise returns the fallback. */
export function withTenantContext<T>(fn: (ctx: TenantContext) => T, fallback: T): T {
  const ctx = getTenantContext();
  if (!ctx) return fallback;
  return fn(ctx);
}
