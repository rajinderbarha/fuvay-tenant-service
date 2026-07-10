"use client";
import React, { useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Input, Badge, Spinner } from "../../../components/shared/ui";
import { ProfilePhotoUploader } from "../../../components/shared/ProfilePhotoUploader";
import { profileApi, type MediaAsset, type UpdateUserProfilePayload } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { Shield, Mail, CalendarDays, User, Globe, Clock } from "lucide-react";

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "ta", label: "Tamil" },
  { value: "te", label: "Telugu" },
  { value: "kn", label: "Kannada" },
  { value: "ml", label: "Malayalam" },
  { value: "mr", label: "Marathi" },
  { value: "bn", label: "Bengali" },
  { value: "gu", label: "Gujarati" },
  { value: "pa", label: "Punjabi" },
  { value: "ur", label: "Urdu" },
];

const TIMEZONES = [
  { value: "UTC",                  label: "UTC" },
  { value: "Asia/Kolkata",         label: "India (IST, UTC+5:30)" },
  { value: "Asia/Dubai",           label: "Dubai (GST, UTC+4)" },
  { value: "Asia/Singapore",       label: "Singapore (SGT, UTC+8)" },
  { value: "Asia/Tokyo",           label: "Tokyo (JST, UTC+9)" },
  { value: "Europe/London",        label: "London (GMT/BST)" },
  { value: "Europe/Paris",         label: "Paris (CET/CEST)" },
  { value: "America/New_York",     label: "New York (ET)" },
  { value: "America/Chicago",      label: "Chicago (CT)" },
  { value: "America/Los_Angeles",  label: "Los Angeles (PT)" },
  { value: "America/Sao_Paulo",    label: "São Paulo (BRT)" },
  { value: "Australia/Sydney",     label: "Sydney (AEST)" },
];

const selectStyle: React.CSSProperties = {
  width: "100%", padding: "8px 12px", fontSize: 13,
  border: "1px solid var(--border)", borderRadius: 8,
  background: "var(--surface)", color: "var(--text-primary)",
  outline: "none", cursor: "pointer",
};

export default function AdminProfilePage() {
  const profile = useApi(() => profileApi.getProfile(), []);

  const [fullName,    setFullName]    = useState("");
  const [displayName, setDisplayName] = useState("");
  const [language,   setLanguage]    = useState("en");
  const [timezone,   setTimezone]    = useState("UTC");
  const [avatarUrl,  setAvatarUrl]   = useState<string | null>(null);
  const [toast,      setToast]       = useState("");
  const [toastType,  setToastType]   = useState<"success" | "error">("success");

  React.useEffect(() => {
    if (profile.data) {
      setFullName(profile.data.full_name ?? "");
      setDisplayName(profile.data.display_name ?? "");
      setLanguage(profile.data.language ?? "en");
      setTimezone(profile.data.timezone ?? "UTC");
      setAvatarUrl(profile.data.avatar_url ?? null);
    }
  }, [profile.data]);

  const notify = (msg: string, type: "success" | "error" = "success") => {
    setToast(msg); setToastType(type);
    setTimeout(() => setToast(""), 3500);
  };

  const saveProfile = useAction(async () => {
    const payload: UpdateUserProfilePayload = {};
    const d = profile.data;
    if (fullName.trim() && fullName !== d?.full_name)      payload.full_name    = fullName.trim();
    if (displayName !== (d?.display_name ?? ""))            payload.display_name = displayName.trim() || undefined;
    if (language !== (d?.language ?? "en"))                 payload.language     = language;
    if (timezone !== (d?.timezone ?? "UTC"))                payload.timezone     = timezone;

    if (Object.keys(payload).length === 0) { notify("No changes to save."); return; }
    await profileApi.updateProfile(payload);
    await profile.refetch();
    notify("Profile updated.");
  });

  const isDirty =
    fullName    !== (profile.data?.full_name    ?? "") ||
    displayName !== (profile.data?.display_name ?? "") ||
    language    !== (profile.data?.language     ?? "en") ||
    timezone    !== (profile.data?.timezone     ?? "UTC");

  if (profile.loading) return (
    <AdminLayout activeNav="account">
      <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}><Spinner /></div>
    </AdminLayout>
  );

  const user = profile.data;

  return (
    <AdminLayout activeNav="account">
      <SectionHeader title="My Profile" subtitle="Manage your profile photo, display preferences, and personal details." />

      {toast && (
        <div style={{
          marginBottom: 16, padding: "10px 16px", borderRadius: 10,
          background: toastType === "success" ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toastType === "success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toastType === "success" ? "var(--success-text)" : "var(--danger)",
          fontSize: 13, fontWeight: 500,
        }}>{toast}</div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 24, alignItems: "start" }}>

        {/* Left column: photo + account summary */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0, alignSelf: "flex-start" }}>
              Profile Photo
            </h3>
            <ProfilePhotoUploader
              ownerType="admin"
              displayName={user?.full_name}
              currentPreviewUrl={avatarUrl}
              currentMediaId={user?.profile_photo_media_id ?? null}
              size="xl"
              onUploaded={(a: MediaAsset) => {
                setAvatarUrl(a.preview_url ?? a.public_url ?? null);
                notify("Photo updated.");
                profile.refetch();
              }}
              onRemoved={() => {
                setAvatarUrl(null);
                notify("Photo removed.");
                profile.refetch();
              }}
            />
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", textAlign: "center", margin: 0, lineHeight: 1.5 }}>
              JPEG or PNG · max 5 MB
            </p>
          </Card>

          <Card style={{ padding: 18 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", margin: "0 0 12px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Account
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <InfoRow icon={<Mail size={13} />}        label="Email"      value={user?.email ?? "—"} />
              <InfoRow icon={<Shield size={13} />}      label="Role"       value={<Badge variant="info">{user?.role?.replace(/_/g, " ").toUpperCase() ?? "—"}</Badge>} />
              <InfoRow icon={<User size={13} />}        label="Status"     value={<Badge variant={user?.is_active !== false ? "success" : "danger"}>{user?.is_active !== false ? "Active" : "Inactive"}</Badge>} />
              <InfoRow icon={<CalendarDays size={13} />} label="Login"     value={user?.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : "—"} />
              <InfoRow icon={<Shield size={13} />}      label="MFA"        value={<Badge variant={user?.is_mfa_enabled ? "success" : "warning"}>{user?.is_mfa_enabled ? "On" : "Off"}</Badge>} />
            </div>
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <a href="/admin/account" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none", fontWeight: 500 }}>
                Security Settings →
              </a>
            </div>
          </Card>
        </div>

        {/* Right column: editable fields */}
        <Card style={{ padding: 28 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 22px" }}>Edit Profile</h3>

          <div style={{ display: "grid", gap: 18 }}>
            <Field label="Full Name" required>
              <Input value={fullName} onChange={v => setFullName(v)} placeholder="Your full name" />
            </Field>

            <Field label="Display Name" hint="Shown in the platform header. Defaults to full name if blank.">
              <Input value={displayName} onChange={v => setDisplayName(v)} placeholder="e.g. Super Admin" />
            </Field>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Field label="Language" icon={<Globe size={12} />}>
                <select value={language} onChange={e => setLanguage(e.target.value)} style={selectStyle}>
                  {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </Field>

              <Field label="Timezone" icon={<Clock size={12} />}>
                <select value={timezone} onChange={e => setTimezone(e.target.value)} style={selectStyle}>
                  {TIMEZONES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </Field>
            </div>

            {/* Email — read-only */}
            <Field label="Email" hint="Email cannot be changed here. Contact the platform team.">
              <div style={{
                padding: "8px 12px", fontSize: 13, borderRadius: 8,
                background: "var(--surface-sunken, #f5f5f5)", border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}>
                {user?.email ?? "—"}
              </div>
            </Field>
          </div>

          <div style={{ marginTop: 24, display: "flex", gap: 10, alignItems: "center" }}>
            <Btn
              onClick={saveProfile.execute}
              loading={saveProfile.loading}
              disabled={!isDirty || !fullName.trim()}
            >
              Save Changes
            </Btn>
            {isDirty && (
              <button
                onClick={() => {
                  setFullName(profile.data?.full_name ?? "");
                  setDisplayName(profile.data?.display_name ?? "");
                  setLanguage(profile.data?.language ?? "en");
                  setTimezone(profile.data?.timezone ?? "UTC");
                }}
                style={{
                  padding: "7px 14px", fontSize: 13, borderRadius: 8, cursor: "pointer",
                  border: "1px solid var(--border)", background: "transparent",
                  color: "var(--text-secondary)",
                }}
              >
                Cancel
              </button>
            )}
          </div>
        </Card>
      </div>
    </AdminLayout>
  );
}

function Field({ label, children, hint, required, icon }: {
  label: string; children: React.ReactNode;
  hint?: string; required?: boolean; icon?: React.ReactNode;
}) {
  return (
    <div>
      <label style={{
        fontSize: 12, fontWeight: 500, color: "var(--text-tertiary)",
        display: "flex", alignItems: "center", gap: 5, marginBottom: 5,
      }}>
        {icon}{label}{required && <span style={{ color: "var(--danger)" }}> *</span>}
      </label>
      {children}
      {hint && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0", lineHeight: 1.4 }}>{hint}</p>}
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>{icon}</div>
      <span style={{ fontSize: 11, color: "var(--text-tertiary)", width: 52, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}
