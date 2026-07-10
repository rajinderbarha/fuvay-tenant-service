"use client";
import React from "react";
import { Card } from "../shared/ui";
import { TenantStatusBadge, type StatusVariant } from "./TenantStatusBadge";
import { CheckCircle2, XCircle, AlertTriangle, Clock } from "lucide-react";
import { safeDate, safePercent, safeText } from "../../lib/status-format";

export type HeroState = "bookable" | "visible_not_bookable" | "not_visible" | "pending_setup" | "suspended" | "blocked";

export interface HeroProps {
  tenantName: string;
  vertical: string | null;
  isVisible: boolean;
  isBookable: boolean;
  setupCompletionPct: number;
  lastEvaluatedAt: string | null;
  primaryBlockingReason: string | null;
  onFixRequiredActions: () => void;
}

function deriveState(isVisible: boolean, isBookable: boolean): HeroState {
  if (isBookable) return "bookable";
  if (isVisible) return "visible_not_bookable";
  return "not_visible";
}

const STATE_META: Record<HeroState, { label: string; variant: StatusVariant; icon: React.ReactNode; bg: string }> = {
  bookable:              { label: "Visible + Bookable",       variant: "success", icon: <CheckCircle2 size={20}/>, bg: "linear-gradient(135deg, rgba(5,150,105,0.10), rgba(5,150,105,0.02))" },
  visible_not_bookable:  { label: "Visible but Not Bookable",  variant: "warning", icon: <AlertTriangle size={20}/>, bg: "linear-gradient(135deg, rgba(217,119,6,0.10), rgba(217,119,6,0.02))" },
  not_visible:           { label: "Not Visible",               variant: "danger",  icon: <XCircle size={20}/>,      bg: "linear-gradient(135deg, rgba(220,38,38,0.10), rgba(220,38,38,0.02))" },
  pending_setup:         { label: "Pending Setup",              variant: "info",    icon: <Clock size={20}/>,        bg: "linear-gradient(135deg, rgba(37,99,235,0.10), rgba(37,99,235,0.02))" },
  suspended:             { label: "Suspended",                  variant: "danger",  icon: <XCircle size={20}/>,      bg: "linear-gradient(135deg, rgba(220,38,38,0.10), rgba(220,38,38,0.02))" },
  blocked:               { label: "Blocked",                    variant: "danger",  icon: <XCircle size={20}/>,      bg: "linear-gradient(135deg, rgba(220,38,38,0.10), rgba(220,38,38,0.02))" },
};

export function TenantStatusHero(props: HeroProps) {
  const state = deriveState(props.isVisible, props.isBookable);
  const meta = STATE_META[state];

  return (
    <Card padding={0} style={{ overflow: "hidden" }}>
      <div style={{ background: meta.bg, padding: 28, display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", margin: "0 0 4px" }}>
              {safeText(props.tenantName)} · {safeText(props.vertical, "Home Services")}
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {meta.icon}
              <h2 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>{meta.label}</h2>
            </div>
          </div>
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <div>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Customer Visibility</p>
              <TenantStatusBadge label={props.isVisible ? "Visible" : "Not visible"} variant={props.isVisible ? "success" : "warning"}/>
            </div>
            <div>
              <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Bookable Status</p>
              <TenantStatusBadge label={props.isBookable ? "Bookable" : "Not bookable"} variant={props.isBookable ? "success" : "danger"}/>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
          <div style={{ minWidth: 160 }}>
            <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Setup Completion</p>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 100, height: 6, borderRadius: 3, background: "var(--surface-sunken)", overflow: "hidden" }}>
                <div style={{ width: safePercent(props.setupCompletionPct), height: "100%", background: "var(--brand)", borderRadius: 3 }}/>
              </div>
              <span style={{ fontSize: 13, fontWeight: 700 }}>{safePercent(props.setupCompletionPct)}</span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "0 0 2px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Last Recalculated</p>
            <p style={{ fontSize: 13, margin: 0 }}>{safeDate(props.lastEvaluatedAt)}</p>
          </div>
        </div>

        {!props.isBookable && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12,
            padding: "12px 16px", borderRadius: 10, background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 700, margin: "0 0 2px" }}>Status: Not Bookable</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                {safeText(props.primaryBlockingReason, "Complete the required setup items below to become bookable.")}
              </p>
            </div>
            <button onClick={props.onFixRequiredActions} style={{
              fontSize: 12, fontWeight: 700, padding: "8px 16px", borderRadius: 8, border: "none",
              background: "var(--brand)", color: "white", cursor: "pointer", flexShrink: 0,
            }}>
              Fix Required Actions
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}
