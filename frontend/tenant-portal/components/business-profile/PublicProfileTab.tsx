"use client";
import React, { useState } from "react";
import { Card, Badge } from "../shared/ui";
import { businessProfileApi, type BusinessProfileOverview } from "../../lib/api";

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
};

export function PublicProfileTab({ profile, onSaved }: { profile: BusinessProfileOverview; onSaved: () => void }) {
  const [description, setDescription] = useState(profile.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function save() {
    setSaving(true); setError(null); setSaved(false);
    try {
      await businessProfileApi.update({ description });
      setSaved(true);
      onSaved();
    } catch {
      setError("Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 20, alignItems: "flex-start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Business description</p>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={5}
            placeholder="Describe your business for customers…" style={{ ...inputStyle, resize: "vertical" }}/>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
            <button onClick={save} disabled={saving} style={{
              padding: "8px 16px", borderRadius: 8, border: "none", background: "var(--brand)", color: "#fff",
              fontSize: 12.5, fontWeight: 700, cursor: saving ? "default" : "pointer", opacity: saving ? 0.6 : 1,
            }}>
              {saving ? "Saving…" : "Save changes"}
            </button>
            {saved && <span style={{ fontSize: 12, color: "var(--success-text)" }}>Saved.</span>}
            {error && <span style={{ fontSize: 12, color: "var(--danger-text)" }}>{error}</span>}
          </div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
            Display name changes are subject to verification policy and may trigger a change request — edit it from the Legal & Verification tab.
          </p>
        </Card>
      </div>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Customer preview</p>
        <div style={{ borderRadius: 12, border: "1px solid var(--border)", overflow: "hidden" }}>
          <div style={{ height: 70, background: "linear-gradient(135deg, var(--surface-sunken), var(--accent-muted))" }}/>
          <div style={{ padding: 14 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 8 }}>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--brand)", color: "#fff",
                display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>
                {(profile.business_name ?? "?")[0]?.toUpperCase()}
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{profile.business_name}</p>
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{profile.rating.average_rating} ★ ({profile.rating.total_reviews})</p>
              </div>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>{description || "No description yet."}</p>
            <Badge variant="success" size="sm" >Verified</Badge>
          </div>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>
          Shown only once ServiceOS matches this business to a customer's request or an active job — never for provider browsing.
        </p>
      </Card>
    </div>
  );
}
