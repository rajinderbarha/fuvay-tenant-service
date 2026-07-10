"use client";
import React from "react";
import Link from "next/link";
import { Card } from "../shared/ui";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, ArrowRight } from "lucide-react";
import type { RequiredAction } from "../../lib/status-format";
import { safeDate } from "../../lib/status-format";

const SEVERITY_META = {
  critical: { icon: <AlertCircle size={16}/>,   color: "#dc2626", bg: "rgba(220,38,38,0.05)",  border: "rgba(220,38,38,0.18)" },
  warning:  { icon: <AlertTriangle size={16}/>, color: "#d97706", bg: "rgba(217,119,6,0.06)",  border: "rgba(217,119,6,0.20)" },
  info:     { icon: <Info size={16}/>,          color: "#2563eb", bg: "rgba(37,99,235,0.05)",  border: "rgba(37,99,235,0.18)" },
};

export function TenantStatusActionCenter({ actions, lastCheckedAt }: { actions: RequiredAction[]; lastCheckedAt: string | null }) {
  return (
    <Card padding={0}>
      <div style={{ padding: "16px 20px", borderBottom: actions.length > 0 ? "1px solid var(--border)" : "none" }}>
        <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Required Actions</p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
          {actions.length === 0
            ? "All required setup checks are complete."
            : `${actions.length} item${actions.length === 1 ? "" : "s"} need attention before you're fully bookable.`}
        </p>
      </div>

      {actions.length === 0 ? (
        <div style={{ padding: 24, display: "flex", alignItems: "center", gap: 12 }}>
          <CheckCircle2 size={22} style={{ color: "#059669" }}/>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>All required setup checks are complete.</p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>Your provider profile is ready for customer visibility.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {actions.map(a => {
            const m = SEVERITY_META[a.severity];
            return (
              <div key={a.code} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 20px",
                borderBottom: "1px solid var(--border)", background: m.bg }}>
                <span style={{ color: m.color, flexShrink: 0, marginTop: 1 }}>{m.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>{a.title}</p>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 4px" }}>{a.reason}</p>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, fontFamily: "monospace" }}>
                    Rule: {a.ruleKey} · Last checked: {safeDate(lastCheckedAt)}
                  </p>
                </div>
                <Link href={a.route} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none",
                  display: "flex", alignItems: "center", gap: 4, flexShrink: 0, whiteSpace: "nowrap" }}>
                  {a.cta} <ArrowRight size={12}/>
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
