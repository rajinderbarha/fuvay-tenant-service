"use client";
import React, { useState } from "react";
import { User, Shield, ShieldAlert, AlertTriangle, ExternalLink } from "lucide-react";
import { Card, Badge } from "../shared/ui";

export function ConfigurationOwnershipCard() {
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Configuration ownership</p>
      <OwnershipRow icon={<User size={14}/>} iconBg="var(--success-bg)" iconColor="var(--success-text)"
        title="Tenant controlled" desc="You can edit these settings." example="Examples: timezone, contacts, default hours"/>
      <OwnershipRow icon={<Shield size={14}/>} iconBg="var(--info-bg)" iconColor="var(--info-text)"
        title="ServiceOS controlled" desc="These are platform rules." example="Examples: matching algorithm, lifecycle transitions"/>
      <OwnershipRow icon={<ShieldAlert size={14}/>} iconBg="var(--warning-bg)" iconColor="var(--warning-text)"
        title="Admin policy" desc="Set by ServiceOS administrators." example="Examples: deposit per qualifying technician, usage credit"/>
    </Card>
  );
}

function OwnershipRow({ icon, iconBg, iconColor, title, desc, example }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; title: string; desc: string; example: string;
}) {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
      <span style={{ width: 28, height: 28, borderRadius: "50%", background: iconBg, color: iconColor, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</span>
      <div>
        <p style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{title}</p>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "2px 0" }}>{desc}</p>
        <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: 0, fontStyle: "italic" }}>{example}</p>
      </div>
    </div>
  );
}

export function WorkspaceStatusCard({ status, lastUpdatedAt }: { status: string; lastUpdatedAt: string | null }) {
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Workspace status</p>
      <Badge variant={status === "active" ? "success" : "muted"} size="sm">{status === "active" ? "Active" : status}</Badge>
      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-tertiary)" }}>Last updated</span>
          <span style={{ color: "var(--text-secondary)" }}>{lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"}</span>
        </div>
      </div>
    </Card>
  );
}

export function UnsavedChangesCard({ count, onReview }: { count: number; onReview: () => void }) {
  if (count === 0) return null;
  return (
    <Card style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <AlertTriangle size={16} style={{ color: "var(--warning-text)", flexShrink: 0, marginTop: 1 }}/>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 4px" }}>Unsaved changes</p>
          <p style={{ fontSize: 12, color: "var(--warning-text)", margin: "0 0 8px" }}>You have {count} unsaved change{count === 1 ? "" : "s"}.</p>
          <button onClick={onReview} style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
            Review changes
          </button>
        </div>
      </div>
    </Card>
  );
}

export function DangerZoneCard() {
  const [showGap, setShowGap] = useState(false);
  return (
    <Card style={{ border: "1px solid var(--danger-border)" }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--danger-text)", margin: "0 0 8px" }}>Danger zone</p>
      {showGap ? (
        <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          A self-service deactivation-request flow doesn't exist on the backend yet — this isn't wired to a real endpoint, so no request was actually submitted. Contact ServiceOS support to request deactivation today.
        </p>
      ) : (
        <>
          <button onClick={() => setShowGap(true)} style={{
            display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 8,
            border: "1px solid var(--danger-border)", background: "transparent", color: "var(--danger-text)",
            fontSize: 12.5, fontWeight: 700, cursor: "pointer", marginBottom: 10,
          }}>
            Request workspace deactivation <ExternalLink size={12}/>
          </button>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0, lineHeight: 1.6 }}>
            Prevents new operations after approval/policy handling. Does not erase historical records — active jobs, complaints,
            finance records and legal retention are handled first. Requires owner permission and confirmation.
          </p>
        </>
      )}
    </Card>
  );
}
