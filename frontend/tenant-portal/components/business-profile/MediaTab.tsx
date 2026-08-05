"use client";
import React from "react";
import { Card, Badge } from "../shared/ui";
import { ProfilePhotoUploader } from "../shared/ProfilePhotoUploader";
import type { BusinessProfileOverview } from "../../lib/api";

export function MediaTab({ profile, onChanged }: { profile: BusinessProfileOverview; onChanged: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 720 }}>
      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Business logo</p>
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "0 0 14px" }}>Square image, shown on your public profile and in search results.</p>
        <ProfilePhotoUploader ownerType="provider_business" currentPreviewUrl={profile.logo_url}
          currentMediaId={profile.business_logo_media_id} displayName={profile.business_name} size="lg"
          onUploaded={onChanged} onRemoved={onChanged}/>
      </Card>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Storefront / cover photo</p>
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "0 0 14px" }}>Wide banner shown at the top of your public profile.</p>
        <ProfilePhotoUploader ownerType="provider_shop" currentMediaId={profile.shop_photo_media_id}
          displayName={profile.business_name} size="lg" onUploaded={onChanged} onRemoved={onChanged}/>
      </Card>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Verification documents</p>
        {profile.documents.length === 0 ? (
          <p style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>
            No documents uploaded yet. Upload business documents from the setup workspace's Documents step.
          </p>
        ) : profile.documents.map(d => (
          <div key={d.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>{d.label ?? d.doc_type}</span>
            <Badge variant={d.status === "verified" ? "success" : d.status === "rejected" ? "danger" : "warning"} size="sm">{d.status.replace(/_/g, " ")}</Badge>
          </div>
        ))}
      </Card>
    </div>
  );
}
