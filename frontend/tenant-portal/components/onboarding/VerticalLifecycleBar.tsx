"use client";
import React from "react";
import { Check } from "lucide-react";
import { Card } from "../shared/ui";
import type { HomeServicesLifecycleStage } from "../../lib/api";

const STAGE_LABELS: Record<string, string> = {
  WORKSPACE: "Workspace",
  SETUP: "Setup",
  ADMIN_REVIEW: "Admin Review",
  ACTIVATION: "Activation",
  GO_LIVE: "Go Live",
};

export function VerticalLifecycleBar({ stages }: { stages: HomeServicesLifecycleStage[] }) {
  return (
    <Card padding={0} style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", padding: "22px 24px", overflowX: "auto" }}
        role="list" aria-label="Onboarding lifecycle progress">
        {stages.map((stage, i) => {
          const label = STAGE_LABELS[stage.key] ?? stage.key;
          const isLast = i === stages.length - 1;
          return (
            <React.Fragment key={stage.key}>
              <div role="listitem" style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 96, flexShrink: 0 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: "50%", display: "flex", alignItems: "center",
                  justifyContent: "center", fontWeight: 700, fontSize: 13,
                  background: stage.status === "COMPLETED" ? "var(--success)"
                    : stage.status === "CURRENT" ? "var(--brand)" : "var(--surface-sunken)",
                  color: stage.status === "COMPLETED" || stage.status === "CURRENT" ? "var(--text-on-brand)" : "var(--text-tertiary)",
                  border: stage.status === "UPCOMING" ? "1px solid var(--border)" : "none",
                }}>
                  {stage.status === "COMPLETED" ? <Check size={16}/> : i + 1}
                </div>
                <p style={{
                  fontSize: 13, fontWeight: stage.status === "CURRENT" ? 700 : 500, margin: "8px 0 0",
                  color: stage.status === "UPCOMING" ? "var(--text-tertiary)" : "var(--text-primary)",
                  textAlign: "center",
                }}>{label}</p>
                <p style={{
                  fontSize: 11, margin: "2px 0 0", textAlign: "center",
                  color: stage.status === "COMPLETED" ? "var(--success-text)"
                    : stage.status === "CURRENT" ? "var(--brand)" : "var(--text-tertiary)",
                  fontWeight: 600,
                }}>
                  {stage.status === "COMPLETED" ? "Completed" : stage.status === "CURRENT" ? "In progress" : "Upcoming"}
                </p>
                {stage.status === "CURRENT" && (
                  <p style={{ fontSize: 10, fontWeight: 700, color: "var(--brand)", margin: "4px 0 0", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                    You are here
                  </p>
                )}
              </div>
              {!isLast && (
                <div aria-hidden style={{
                  flex: 1, height: 2, marginTop: 17, minWidth: 24,
                  background: stage.status === "COMPLETED" ? "var(--success)" : "var(--border)",
                }}/>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </Card>
  );
}
