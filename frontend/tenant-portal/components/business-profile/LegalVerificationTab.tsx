"use client";
import React from "react";
import { Lock, Info } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import type { BusinessProfileOverview } from "../../lib/api";

function mask(v: string | null): string {
  if (!v) return "—";
  if (v.length <= 4) return v;
  return v.slice(0, 2) + "•".repeat(Math.max(v.length - 4, 3)) + v.slice(-2);
}

function statusVariant(v: string): "success" | "warning" | "danger" | "muted" {
  if (["verified", "approved", "active"].includes(v)) return "success";
  if (v === "changes_pending_review" || v === "pending") return "warning";
  if (v === "rejected") return "danger";
  return "muted";
}

export function LegalVerificationTab({ profile }: { profile: BusinessProfileOverview }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 780 }}>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Legal identity</p>
          <Badge variant={statusVariant(profile.verification_status)} size="sm">{profile.verification_status.replace(/_/g, " ")}</Badge>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <LegalField label="Legal business name" value={profile.legal_name}/>
          <LegalField label="Entity type" value={profile.business_type}/>
          <LegalField label="Registration number" value={mask(profile.registration_number)}/>
          <LegalField label="GSTIN / tax identity" value={mask(profile.gst_number)}/>
          <LegalField label="Registered address" value={[profile.address_line1, profile.city, profile.state, profile.zipcode].filter(Boolean).join(", ")}/>
          <LegalField label="Owner / authorized representative" value={profile.owner_name}/>
        </div>
      </Card>

      {profile.verification_status === "changes_pending_review" && (
        <Card style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
          <div style={{ display: "flex", gap: 10 }}>
            <Info size={16} style={{ color: "var(--warning-text)", flexShrink: 0, marginTop: 1 }}/>
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 4px" }}>Re-verification in progress</p>
              <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0 }}>
                A verified field was changed. Your currently approved details remain live and in effect while ServiceOS reviews the update — the business is not deactivated during this period.
              </p>
            </div>
          </div>
        </Card>
      )}

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}>
          <Lock size={13}/> Changing a protected field
        </p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Legal business name, registration number, GSTIN, and registered address are locked once verified. Editing any of them
          creates a change request that ServiceOS must review and approve before it takes effect — your currently approved
          values stay live in the meantime.
        </p>
      </Card>
    </div>
  );
}

function LegalField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{label}</span>
        <Lock size={10} style={{ color: "var(--text-tertiary)" }}/>
      </div>
      <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, fontWeight: 500 }}>{value || "—"}</p>
    </div>
  );
}
