"use client";
import React, { useCallback } from "react";
import { Card, Badge, Btn } from "../shared/ui";
import { CheckCircle2, XCircle, Zap, ArrowRight, RefreshCw } from "lucide-react";
import { providerStatusApi, type ProviderStatusResult } from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { useAction } from "../../hooks/useApi";
import Link from "next/link";

export function BookabilityStatusWidget() {
  const status = useApi(useCallback(() => providerStatusApi.get(), []));

  const refreshAction = useAction(
    useCallback(() => providerStatusApi.refresh(), []),
    { onSuccess: () => status.refetch() }
  );

  const s: ProviderStatusResult | null = status.data ?? null;

  if (status.loading) {
    return (
      <Card padding={16}>
        <div style={{ height: 60, background: "var(--surface-sunken)", borderRadius: 6, animation: "pulse 1.5s infinite" }} />
      </Card>
    );
  }

  if (!s || status.error) return null;

  const allGood = s.is_visible && s.is_bookable;
  const totalBlockers = (s.visibility_blockers?.length ?? 0) + (s.bookability_blockers?.length ?? 0);

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8,
            background: allGood ? "rgba(5,150,105,0.1)" : "rgba(220,38,38,0.08)",
            display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap size={16} style={{ color: allGood ? "var(--success)" : "var(--danger)" }} />
          </div>
          <div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Platform Status</p>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "2px 0 0" }}>
              {allGood ? "Live & Accepting Bookings" : "Action Required"}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <Btn size="sm" variant="secondary" onClick={() => refreshAction.execute()} disabled={refreshAction.loading}>
            <RefreshCw size={12} />
          </Btn>
          <Link href="/provider/status" style={{ fontSize: 12, color: "var(--brand)", textDecoration: "none",
            display: "flex", alignItems: "center", gap: 3, fontWeight: 500, padding: "4px 8px",
            border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface)" }}>
            Details <ArrowRight size={11} />
          </Link>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, padding: "8px 10px",
          background: s.is_visible ? "rgba(5,150,105,0.06)" : "rgba(220,38,38,0.06)",
          borderRadius: 6, border: `1px solid ${s.is_visible ? "rgba(5,150,105,0.2)" : "rgba(220,38,38,0.2)"}` }}>
          {s.is_visible
            ? <CheckCircle2 size={13} style={{ color: "var(--success)", flexShrink: 0 }} />
            : <XCircle size={13} style={{ color: "var(--danger)", flexShrink: 0 }} />}
          <span style={{ fontSize: 12, fontWeight: 500, color: s.is_visible ? "var(--success)" : "var(--danger)" }}>
            {s.is_visible ? "Visible" : "Hidden"}
          </span>
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, padding: "8px 10px",
          background: s.is_bookable ? "rgba(5,150,105,0.06)" : "rgba(220,38,38,0.06)",
          borderRadius: 6, border: `1px solid ${s.is_bookable ? "rgba(5,150,105,0.2)" : "rgba(220,38,38,0.2)"}` }}>
          {s.is_bookable
            ? <CheckCircle2 size={13} style={{ color: "var(--success)", flexShrink: 0 }} />
            : <XCircle size={13} style={{ color: "var(--danger)", flexShrink: 0 }} />}
          <span style={{ fontSize: 12, fontWeight: 500, color: s.is_bookable ? "var(--success)" : "var(--danger)" }}>
            {s.is_bookable ? "Bookable" : "Not Bookable"}
          </span>
        </div>
      </div>

      {totalBlockers > 0 && (
        <div style={{ marginTop: 10, padding: "8px 10px",
          background: "rgba(220,38,38,0.05)", borderRadius: 6, border: "1px solid rgba(220,38,38,0.15)" }}>
          <p style={{ fontSize: 12, color: "var(--danger)", margin: 0 }}>
            {totalBlockers} blocker{totalBlockers > 1 ? "s" : ""} preventing full activation.{" "}
            <Link href="/provider/status" style={{ color: "var(--danger)", fontWeight: 600 }}>View and resolve →</Link>
          </p>
        </div>
      )}
    </Card>
  );
}
