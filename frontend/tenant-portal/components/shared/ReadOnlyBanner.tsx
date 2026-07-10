"use client";
/**
 * ReadOnlyBanner — shown when the current user has a read-only role.
 * Import and render at the top of any page that has mutation actions.
 * The banner is hidden if the user has full write access.
 */
import React from "react";
import { Eye } from "lucide-react";

interface Props {
  role?: string | null;
}

/**
 * Returns true if the given role is read-only (no mutation allowed).
 */
export function isReadOnly(role?: string | null): boolean {
  if (!role) return false;
  const r = role.toLowerCase();
  return r === "tenant_read_only" || r === "read_only" || r.endsWith("_viewer");
}

export default function ReadOnlyBanner({ role }: Props) {
  if (!isReadOnly(role)) return null;
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "10px 16px",
      background: "var(--warning-bg, #fffbeb)",
      border: "1px solid var(--warning-border, #f59e0b)",
      borderRadius: 10,
      marginBottom: 16,
      fontSize: 13,
      color: "var(--warning-text, #92400e)",
    }}>
      <Eye size={15} style={{ flexShrink: 0 }}/>
      <span>
        <strong>View-only mode.</strong> Your account has read-only access. Contact your administrator to request write permissions.
      </span>
    </div>
  );
}
