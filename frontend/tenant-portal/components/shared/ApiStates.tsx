"use client";
/**
 * FRONTEND-CONNECT-01 — Shared API UI-state components (tenant-portal).
 *
 * The error/loading/empty patterns already exist ad-hoc across many pages
 * (see /provider/status/page.tsx for the most complete hand-rolled version).
 * This file is the reusable version so future pages don't hand-roll it again.
 * Uses the same CSS design tokens (var(--*)) as components/shared/ui.tsx.
 */
import React, { useState } from "react";
import { AlertTriangle, Copy, Check, RefreshCw, ShieldOff, Info } from "lucide-react";
import type { ApiError } from "../../lib/api-foundation/error-model";
import { Skeleton, EmptyState } from "./ui";

// ── RequestIdBadge / CopyRequestIdButton ───────────────────────────────────
export function RequestIdBadge({ requestId }: { requestId?: string | null }) {
  if (!requestId) return null;
  return (
    <span style={{
      fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)",
      background: "var(--surface-sunken)", border: "1px solid var(--border)",
      borderRadius: 6, padding: "2px 8px", display: "inline-flex", alignItems: "center", gap: 6,
    }}>
      Request ID: {requestId}
    </span>
  );
}

export function CopyRequestIdButton({ requestId }: { requestId?: string | null }) {
  const [copied, setCopied] = useState(false);
  if (!requestId) return null;
  return (
    <button
      onClick={async () => {
        try { await navigator.clipboard.writeText(requestId); setCopied(true); setTimeout(() => setCopied(false), 1500); }
        catch { /* clipboard unavailable */ }
      }}
      style={{
        display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 500,
        color: "var(--text-secondary)", background: "none", border: "1px solid var(--border)",
        borderRadius: 8, padding: "5px 10px", cursor: "pointer", fontFamily: "inherit",
      }}>
      {copied ? <Check size={12}/> : <Copy size={12}/>}
      {copied ? "Copied" : "Copy Request ID"}
    </button>
  );
}

// ── ApiLoadingState ─────────────────────────────────────────────────────────
export function ApiLoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: 20 }}>
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} height={20}/>)}
    </div>
  );
}

// ── ApiErrorState — Title / Message / Request ID / Retry / Copy ─────────────
export function ApiErrorState({ error, onRetry }: { error: ApiError | string; onRetry?: () => void }) {
  const err: ApiError = typeof error === "string" ? { code: "UNKNOWN_ERROR", message: error } : error;
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center",
      gap: 10, padding: "40px 24px", background: "var(--danger-bg)",
      border: "1px solid var(--danger-border)", borderRadius: 16,
    }}>
      <AlertTriangle size={28} color="var(--danger-text)"/>
      <p style={{ fontSize: 15, fontWeight: 700, color: "var(--danger-text)", margin: 0 }}>Something went wrong</p>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, maxWidth: 440 }}>{err.message}</p>
      {err.request_id && <RequestIdBadge requestId={err.request_id}/>}
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        {onRetry && (
          <button onClick={onRetry} style={{
            display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600,
            color: "var(--text-on-brand)", background: "var(--primary-gradient)", border: "none",
            borderRadius: 999, padding: "8px 16px", cursor: "pointer", fontFamily: "inherit",
          }}><RefreshCw size={13}/> Retry</button>
        )}
        {err.request_id && <CopyRequestIdButton requestId={err.request_id}/>}
      </div>
    </div>
  );
}

// ── ApiPermissionDeniedState ─────────────────────────────────────────────────
export function ApiPermissionDeniedState({ requestId }: { requestId?: string | null }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center",
      gap: 10, padding: "40px 24px", background: "var(--warning-bg)",
      border: "1px solid var(--warning-border)", borderRadius: 16,
    }}>
      <ShieldOff size={28} color="var(--warning-text)"/>
      <p style={{ fontSize: 15, fontWeight: 700, color: "var(--warning-text)", margin: 0 }}>Access Denied</p>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, maxWidth: 440 }}>
        You do not have permission to perform this action.
      </p>
      {requestId && <RequestIdBadge requestId={requestId}/>}
      {requestId && <CopyRequestIdButton requestId={requestId}/>}
    </div>
  );
}

// ── ApiValidationErrorList ───────────────────────────────────────────────────
export function ApiValidationErrorList({ fieldErrors }: { fieldErrors?: Record<string, string[]> }) {
  if (!fieldErrors || Object.keys(fieldErrors).length === 0) return null;
  return (
    <div style={{
      background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
      borderRadius: 12, padding: "12px 16px", display: "flex", flexDirection: "column", gap: 6,
    }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: "var(--danger-text)", margin: 0 }}>Please fix the following:</p>
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {Object.entries(fieldErrors).map(([field, msgs]) => (
          <li key={field} style={{ fontSize: 12, color: "var(--danger-text)" }}>
            <strong>{field}:</strong> {msgs.join(", ")}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── ApiEmptyState — thin wrapper over existing EmptyState for consistency ───
export function ApiEmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return <EmptyState icon={<Info/>} title={title} description={description} action={action}/>;
}
