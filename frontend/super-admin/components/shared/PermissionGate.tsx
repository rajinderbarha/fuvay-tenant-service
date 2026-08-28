"use client";
import { clearSession } from "../../lib/api";
/**
 * FINAL-L5-05M — Reusable direct-route permission guard + shared
 * Permission Denied / read-only presentation components.
 *
 * Backend remains authoritative (rule 1/2) — this only controls what
 * renders client-side; every mutation this gate protects is independently
 * enforced server-side via require_permission(). Permission truth is
 * always usePermissions()'s server-provided array (rule 3/4).
 */
import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { usePermissions } from "../../hooks/usePermissions";
import { SUPER_ADMIN_ONLY } from "../../lib/permission-catalog";
import { Skeleton } from "./ui";

export function PermissionDeniedPage({ parentHref, parentLabel, requestId }: {
  parentHref?: string; parentLabel?: string; requestId?: string | null;
}) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center",
        gap: 12, padding: "64px 24px", maxWidth: 520, margin: "40px auto",
      }}
    >
      <ShieldOff size={32} color="var(--warning-text, #b45309)" aria-hidden="true"/>
      <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Permission denied</h1>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
        You do not have access to this page or action.
        Contact a platform administrator if you believe this is incorrect.
      </p>
      {requestId && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace", margin: 0 }}>
          request_id: {requestId}
        </p>
      )}
      <Link
        href={parentHref ?? "/admin/dashboard"}
        style={{
          marginTop: 8, fontSize: 13, fontWeight: 600, color: "var(--accent, #2563eb)",
          textDecoration: "none",
        }}
      >
        {parentLabel ? `Back to ${parentLabel}` : "Back to Dashboard"}
      </Link>
    </div>
  );
}

export function ReadOnlyNotice() {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
      background: "var(--info-bg, #eff6ff)", border: "1px solid var(--info-border, #bfdbfe)",
      borderRadius: 10, fontSize: 12.5, marginBottom: 16,
    }}>
      <ShieldOff size={14} aria-hidden="true"/>
      <span>
        <strong>View-only access.</strong> You can review this information, but you cannot make changes.
      </span>
    </div>
  );
}

/**
 * Wrap a page's content. Renders a skeleton while permissions are loading
 * (never the protected content, never a false-denied flash), the real
 * page once the read permission resolves true, or PermissionDeniedPage
 * once it resolves false. `requiredPermission` uses the same catalog keys
 * as AdminLayout's NAV_GROUPS (including SUPER_ADMIN_ONLY).
 */
export function RequirePermission({
  requiredPermission, parentHref, parentLabel, children,
}: {
  requiredPermission: string;
  parentHref?: string;
  parentLabel?: string;
  children: React.ReactNode;
}) {
  const { permissions, role, loading, authenticated } = usePermissions();

  if (loading || authenticated === null) {
    return <Skeleton height={320}/>;
  }

  // No confirmed session: render NOTHING and send them to sign in. This has to
  // precede the permission check, because a route requiring "" would otherwise
  // be allowed -- "needs no permission" is not "needs no session", and that is
  // how pages stayed visible on an expired token. clearSession() is idempotent
  // and already redirects.
  if (!authenticated) {
    if (typeof window !== "undefined") clearSession();
    return <Skeleton height={320}/>;
  }

  if (permissions === null) {
    return <Skeleton height={320}/>;
  }

  const allowed = requiredPermission === ""
    ? true
    : requiredPermission === SUPER_ADMIN_ONLY
      ? role === "super_admin"
      : permissions.includes("*") || permissions.includes(requiredPermission);

  if (!allowed) {
    return <PermissionDeniedPage parentHref={parentHref} parentLabel={parentLabel}/>;
  }

  return <>{children}</>;
}
