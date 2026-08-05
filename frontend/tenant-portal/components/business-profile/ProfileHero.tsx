"use client";
import React from "react";
import { Eye, Pencil } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import { resolveMediaUrl } from "../shared/ProfilePhotoUploader";
import type { BusinessProfileOverview } from "../../lib/api";

function statusVariant(status: string): "success" | "muted" {
  return status === "active" ? "success" : "muted";
}
function verificationVariant(v: string): "success" | "warning" | "muted" {
  if (v === "verified" || v === "approved" || v === "active") return "success";
  if (v === "pending" || v === "changes_pending_review") return "warning";
  return "muted";
}
function verificationLabel(v: string): string {
  if (v === "verified" || v === "approved" || v === "active") return "Verified";
  if (v === "changes_pending_review") return "Review pending";
  if (v === "pending") return "Pending review";
  return "Not verified";
}

export function ProfileHero({ profile, onPreview, onEdit }: {
  profile: BusinessProfileOverview; onPreview: () => void; onEdit: () => void;
}) {
  const logoUrl = resolveMediaUrl(profile.logo_url);
  const pct = profile.completeness.percentage;

  return (
    <Card padding={0} style={{ overflow: "hidden", marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "12px 20px 0" }}>
        <button onClick={onPreview} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
          borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
          fontSize: 12.5, fontWeight: 600, cursor: "pointer" }}>
          <Eye size={14}/> Preview public profile
        </button>
        <button onClick={onEdit} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
          borderRadius: 8, border: "none", background: "var(--brand)", color: "#fff",
          fontSize: 12.5, fontWeight: 700, cursor: "pointer" }}>
          <Pencil size={14}/> Edit profile
        </button>
      </div>

      <div style={{ height: 160, margin: "12px 20px 0", borderRadius: 12, overflow: "hidden",
        background: "linear-gradient(135deg, var(--surface-sunken), var(--accent-muted))", position: "relative" }}>
        {/* Cover image: real if the tenant has uploaded a shop photo, honest gradient placeholder otherwise. */}
        {profile.shop_photo_media_id && (
          <div style={{ position: "absolute", inset: 0, background: "var(--surface-sunken)" }}/>
        )}
      </div>

      <div style={{ padding: "0 20px 20px", display: "flex", gap: 16, alignItems: "flex-end" }}>
        <div style={{ width: 72, height: 72, borderRadius: 16, background: "var(--brand)", flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center", border: "4px solid var(--surface)",
          overflow: "hidden", fontSize: 26, fontWeight: 800, color: "#fff", marginTop: -36 }}>
          {logoUrl ? <img src={logoUrl} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }}/> :
            (profile.business_name ?? "?")[0].toUpperCase()}
        </div>

        <div style={{ flex: 1, minWidth: 0, paddingBottom: 4, paddingTop: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{profile.business_name}</h1>
            <Badge variant={statusVariant(profile.status)} size="sm">{profile.status === "active" ? "Active" : profile.status}</Badge>
            <Badge variant={verificationVariant(profile.verification_status)} size="sm">{verificationLabel(profile.verification_status)}</Badge>
            <Badge variant="info" size="sm">Home Services</Badge>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            {profile.description || "No customer-facing description yet."}
          </p>
        </div>

        <div style={{ textAlign: "right", flexShrink: 0, paddingBottom: 4, paddingTop: 12 }}>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Profile completeness</p>
          <p style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>{pct}%</p>
          <div style={{ width: 140, height: 6, borderRadius: 999, background: "var(--surface-sunken)", overflow: "hidden" }}>
            <div style={{ width: `${pct}%`, height: "100%", background: pct >= 80 ? "var(--success-text)" : "var(--warning-text)" }}/>
          </div>
        </div>
      </div>
    </Card>
  );
}
