"use client";
import React from "react";
import { Badge } from "../shared/ui";

export type StatusVariant = "success" | "warning" | "danger" | "info" | "default";

export function TenantStatusBadge({ label, variant, size = "sm" }: { label: string; variant: StatusVariant; size?: "sm" | "md" | "lg" }) {
  return <Badge variant={variant} size={size}>{label}</Badge>;
}

export function TenantStatusSectionError({ title, message, requestId, section, onRetry }: {
  title: string; message: string; requestId?: string | null; section: string; onRetry?: () => void;
}) {
  return (
    <div style={{ padding: 16, borderRadius: 10, border: "1px solid var(--danger-border, #fecaca)",
      background: "var(--danger-bg, #fef2f2)", display: "flex", flexDirection: "column", gap: 8 }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text, #b91c1c)", margin: 0 }}>{title}</p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{message}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, fontFamily: "monospace" }}>
        Failed source: {section}{requestId && ` · Request ID: ${requestId}`}
      </p>
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        {onRetry && (
          <button onClick={onRetry} style={{ fontSize: 12, fontWeight: 600, padding: "6px 12px", borderRadius: 6,
            border: "1px solid var(--danger-border, #fecaca)", background: "transparent", color: "var(--danger-text, #b91c1c)", cursor: "pointer" }}>
            Retry
          </button>
        )}
        {requestId && (
          <button onClick={() => navigator.clipboard?.writeText(requestId)} style={{ fontSize: 12, fontWeight: 600, padding: "6px 12px", borderRadius: 6,
            border: "1px solid var(--border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer" }}>
            Copy Request ID
          </button>
        )}
      </div>
    </div>
  );
}
