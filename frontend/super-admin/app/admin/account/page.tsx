"use client";
import React, { useState } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Input, Badge, Spinner, Modal, AddBtn } from "../../../components/shared/ui";
import { ProfilePhotoUploader } from "../../../components/shared/ProfilePhotoUploader";
import { authApi, type UserSession, type ApiKey, type ApiKeyCreated, type MfaSetup, type MediaAsset } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

export default function AccountPage() {
  const me       = useApi(() => authApi.me(), []);
  const sessions = useApi(() => authApi.getSessions(), []);
  const keys     = useApi(() => authApi.listApiKeys(), []);

  const [tab, setTab]               = useState<"profile"|"security"|"mfa"|"sessions"|"apikeys">("profile");
  const [toast, setToast]           = useState("");
  const [mfaSetup, setMfaSetup]     = useState<MfaSetup | null>(null);
  const [newKeyModal, setNewKeyModal] = useState(false);
  const [newKeyResult, setNewKeyResult] = useState<ApiKeyCreated | null>(null);

  // Profile form
  const [fullName, setFullName] = useState("");
  const [email, setEmail]       = useState("");

  // Password form
  const [currPass, setCurrPass] = useState("");
  const [newPass,  setNewPass]  = useState("");
  const [confPass, setConfPass] = useState("");

  // MFA confirm code
  const [mfaCode,    setMfaCode]    = useState("");
  const [disableCode, setDisableCode] = useState("");

  // New API key form
  const [keyName,   setKeyName]   = useState("");
  const [keyScopes, setKeyScopes] = useState("read");
  const [keyExpiry, setKeyExpiry] = useState("30");

  React.useEffect(() => {
    if (me.data) {
      setFullName(me.data.full_name);
      setEmail(me.data.email);
    }
  }, [me.data]);

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const updateProfile = useAction(async () => {
    await authApi.updateMe({ full_name: fullName });
    await me.refetch();
    notify("Profile updated.");
  });

  const changePass = useAction(async () => {
    if (newPass !== confPass) { notify("Passwords do not match."); return; }
    await authApi.changePassword(currPass, newPass);
    setCurrPass(""); setNewPass(""); setConfPass("");
    notify("Password changed successfully.");
  });

  const startMfa = useAction(async () => {
    const setup = await authApi.setupMfa();
    setMfaSetup(setup);
  });

  const confirmMfa = useAction(async () => {
    await authApi.confirmMfa(mfaCode);
    setMfaSetup(null); setMfaCode("");
    await me.refetch();
    notify("MFA enabled.");
  });

  const disableMfa = useAction(async () => {
    await authApi.disableMfa(disableCode);
    setDisableCode("");
    await me.refetch();
    notify("MFA disabled.");
  });

  const revokeSession = useAction(async (sessionId: string) => {
    await authApi.deleteSession(sessionId);
    await sessions.refetch();
    notify("Session revoked.");
  });

  const logoutAll = useAction(async () => {
    await authApi.logoutAll();
    localStorage.removeItem("serviceos_admin_token");
    localStorage.removeItem("serviceos_admin_refresh");
    window.location.href = "/login";
  });

  const createKey = useAction(async () => {
    const scopes = keyScopes.split(",").map(s => s.trim()).filter(Boolean);
    const result = await authApi.createApiKey(keyName, scopes, parseInt(keyExpiry) || undefined);
    setNewKeyResult(result);
    setKeyName(""); setKeyScopes("read"); setKeyExpiry("30");
    await keys.refetch();
  });

  const deleteKey = useAction(async (keyId: string) => {
    await authApi.deleteApiKey(keyId);
    await keys.refetch();
    notify("API key deleted.");
  });

  const toggleKey = useAction(async (keyId: string, isActive: boolean) => {
    await authApi.updateApiKey(keyId, { is_active: !isActive });
    await keys.refetch();
  });

  const TABS = [
    { id:"profile",  label:"Profile"    },
    { id:"security", label:"Password"   },
    { id:"mfa",      label:"MFA"        },
    { id:"sessions", label:"Sessions"   },
    { id:"apikeys",  label:"API Keys"   },
  ] as const;

  const u = me.data as (typeof me.data & { mfa_enabled?: boolean }) | null;

  return (
    <AdminLayout activeNav="account">
      <div style={{ display:"flex", flexDirection:"column", gap:24 }}>
        <SectionHeader title="My Account" subtitle="Profile, security, sessions and API keys" />

        {toast && (
          <div style={{ padding:"10px 16px", background:"var(--success-bg,#d1fae5)", border:"1px solid var(--success,var(--success))",
            borderRadius:"var(--radius-md)", color:"var(--success-text,#065f46)", fontSize:13 }}>
            {toast}
          </div>
        )}

        {/* Tab bar */}
        <div style={{ display:"flex", gap:4, borderBottom:"1px solid var(--border)", paddingBottom:0 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
              style={{ padding:"8px 16px", border:"none", background:"none", cursor:"pointer",
                fontWeight: tab === t.id ? 700 : 400, fontSize:13,
                color: tab === t.id ? "var(--brand)" : "var(--text-secondary)",
                borderBottom: tab === t.id ? "2px solid var(--brand)" : "2px solid transparent",
                marginBottom:-1 }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* PROFILE */}
        {tab === "profile" && (
          <Card>
            {me.loading ? <Spinner /> : (
              <div style={{ display:"flex", gap:32, alignItems:"flex-start", flexWrap:"wrap" }}>
                {/* Photo column */}
                <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:10, minWidth:120 }}>
                  <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:0 }}>Profile Photo</p>
                  <ProfilePhotoUploader
                    ownerType="admin"
                    displayName={u?.full_name}
                    currentPreviewUrl={(u as unknown as { avatar_url?: string })?.avatar_url ?? null}
                    currentMediaId={(u as unknown as { profile_photo_media_id?: string })?.profile_photo_media_id ?? null}
                    size="lg"
                    onUploaded={(_a: MediaAsset) => { notify("Photo updated."); me.refetch(); }}
                    onRemoved={() => { notify("Photo removed."); me.refetch(); }}
                  />
                  <Link href="/admin/profile" style={{ fontSize:11, color:"var(--accent)", textDecoration:"none" }}>
                    Full profile →
                  </Link>
                </div>
                {/* Fields column */}
                <div style={{ display:"flex", flexDirection:"column", gap:16, flex:1, maxWidth:400 }}>
                  <Input label="Full Name" value={fullName} onChange={v => setFullName(v)} />
                  <Input label="Email" value={email} onChange={() => {}} hint="Email cannot be changed here." />
                  <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                    <Badge variant={u?.role === "super_admin" ? "success" : "info"}>{u?.role}</Badge>
                    {u && <span style={{ fontSize:12, color:"var(--text-secondary)" }}>ID: {u.id}</span>}
                  </div>
                  <Btn onClick={updateProfile.execute} loading={updateProfile.loading}>Save Changes</Btn>
                  {updateProfile.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{updateProfile.error}</p>}
                </div>
              </div>
            )}
          </Card>
        )}

        {/* PASSWORD */}
        {tab === "security" && (
          <Card>
            <div style={{ display:"flex", flexDirection:"column", gap:16, maxWidth:480 }}>
              <p style={{ fontWeight:600, margin:"0 0 4px" }}>Change Password</p>
              <Input label="Current Password" type="password" value={currPass} onChange={v => setCurrPass(v)} />
              <Input label="New Password"     type="password" value={newPass}  onChange={v => setNewPass(v)} />
              <Input label="Confirm Password" type="password" value={confPass} onChange={v => setConfPass(v)} />
              <Btn onClick={changePass.execute} loading={changePass.loading}>Change Password</Btn>
              {changePass.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{changePass.error}</p>}
            </div>
          </Card>
        )}

        {/* MFA */}
        {tab === "mfa" && (
          <Card>
            <div style={{ display:"flex", flexDirection:"column", gap:16, maxWidth:480 }}>
              {me.loading ? <Spinner /> : (
                <>
                  <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                    <p style={{ fontWeight:600, margin:0 }}>Two-Factor Authentication</p>
                    <Badge variant={u?.mfa_enabled ? "success" : "warning"}>
                      {u?.mfa_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>

                  {!u?.mfa_enabled && !mfaSetup && (
                    <Btn onClick={startMfa.execute} loading={startMfa.loading}>Enable MFA</Btn>
                  )}

                  {mfaSetup && (
                    <>
                      <p style={{ fontSize:13, color:"var(--text-secondary)" }}>
                        Scan this QR code with your authenticator app:
                      </p>
                      <img src={mfaSetup.qr_code_url} alt="MFA QR" style={{ width:200, height:200, border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }} />
                      <p style={{ fontSize:12, color:"var(--text-secondary)" }}>
                        Or enter secret manually: <code style={{ background:"var(--surface-alt)", padding:"2px 6px", borderRadius:4 }}>{mfaSetup.secret}</code>
                      </p>
                      <Input label="Verification Code" value={mfaCode} onChange={v => setMfaCode(v)}
                        hint="Enter the 6-digit code from your authenticator" />
                      <Btn onClick={confirmMfa.execute} loading={confirmMfa.loading}>Confirm & Enable</Btn>
                    </>
                  )}

                  {u?.mfa_enabled && (
                    <>
                      <Input label="Current MFA Code" value={disableCode} onChange={v => setDisableCode(v)}
                        hint="Enter your current 6-digit code to disable MFA" />
                      <Btn variant="danger" onClick={disableMfa.execute} loading={disableMfa.loading}>Disable MFA</Btn>
                    </>
                  )}
                </>
              )}
            </div>
          </Card>
        )}

        {/* SESSIONS */}
        {tab === "sessions" && (
          <Card>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <p style={{ fontWeight:600, margin:0 }}>Active Sessions ({sessions.data?.active_sessions ?? 0})</p>
              <Btn variant="danger" size="sm" onClick={logoutAll.execute} loading={logoutAll.loading}>
                Revoke All
              </Btn>
            </div>
            {sessions.loading ? <Spinner /> : (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {(sessions.data?.sessions ?? []).map((s: UserSession) => (
                  <div key={s.session_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)", background:"var(--surface)" }}>
                    <div>
                      <p style={{ margin:"0 0 2px", fontSize:13, fontWeight:500 }}>
                        {s.ip_address}
                        {s.is_current && <span style={{ marginLeft:8 }}><Badge variant="success">Current</Badge></span>}
                      </p>
                      <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                        Last seen: {new Date(s.last_seen_at).toLocaleString()} · Expires: {new Date(s.expires_at).toLocaleString()}
                      </p>
                    </div>
                    {!s.is_current && (
                      <Btn variant="ghost" size="sm"
                        onClick={() => revokeSession.execute(s.session_id)}
                        loading={revokeSession.loading}>
                        Revoke
                      </Btn>
                    )}
                  </div>
                ))}
                {(sessions.data?.sessions ?? []).length === 0 && (
                  <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>No active sessions.</p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* API KEYS */}
        {tab === "apikeys" && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Card>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
                <p style={{ fontWeight:600, margin:0 }}>API Keys ({keys.data?.total ?? 0})</p>
                <AddBtn label="New Key" onClick={() => setNewKeyModal(true)}/>
              </div>
              {keys.loading ? <Spinner /> : (
                <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                  {(keys.data?.keys ?? []).map((k: ApiKey) => (
                    <div key={k.key_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                      padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                      <div>
                        <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:4 }}>
                          <p style={{ margin:0, fontSize:13, fontWeight:600 }}>{k.name}</p>
                          <Badge variant={k.is_active ? "success" : "muted"}>{k.is_active ? "Active" : "Inactive"}</Badge>
                        </div>
                        <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                          {k.prefix}••••  ·  Scopes: {k.scopes.join(", ")}  ·  Created: {new Date(k.created_at).toLocaleDateString()}
                          {k.expires_at && `  ·  Expires: ${new Date(k.expires_at).toLocaleDateString()}`}
                          {k.last_used_at && `  ·  Last used: ${new Date(k.last_used_at).toLocaleString()}`}
                        </p>
                      </div>
                      <div style={{ display:"flex", gap:8 }}>
                        <Btn variant="ghost" size="sm" onClick={() => toggleKey.execute(k.key_id, k.is_active)}>
                          {k.is_active ? "Disable" : "Enable"}
                        </Btn>
                        <Btn variant="danger" size="sm" onClick={() => deleteKey.execute(k.key_id)}>Delete</Btn>
                      </div>
                    </div>
                  ))}
                  {(keys.data?.keys ?? []).length === 0 && (
                    <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>No API keys yet.</p>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* New API Key Modal */}
      <Modal open={newKeyModal} onClose={() => { setNewKeyModal(false); setNewKeyResult(null); }} title="Create API Key" size="md">
        {newKeyResult ? (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ padding:12, background:"var(--success-bg,#d1fae5)", borderRadius:"var(--radius-md)", border:"1px solid var(--success,var(--success))" }}>
              <p style={{ margin:"0 0 8px", fontWeight:600, color:"var(--success-text,#065f46)" }}>API Key Created</p>
              <p style={{ margin:"0 0 4px", fontSize:12, color:"var(--success-text,#065f46)" }}>Copy this key now — it will not be shown again:</p>
              <code style={{ display:"block", wordBreak:"break-all", fontSize:12, padding:"8px 10px",
                background:"white", border:"1px solid var(--border)", borderRadius:6 }}>
                {newKeyResult.secret_key}
              </code>
            </div>
            <Btn onClick={() => { setNewKeyModal(false); setNewKeyResult(null); }}>Done</Btn>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Key Name" value={keyName} onChange={v => setKeyName(v)}
              hint="A descriptive name for this key" />
            <Input label="Scopes" value={keyScopes} onChange={v => setKeyScopes(v)}
              hint="Comma-separated: read, write, admin" />
            <Input label="Expires in (days)" value={keyExpiry} onChange={v => setKeyExpiry(v)}
              hint="Leave blank for no expiry" />
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <Btn variant="ghost" onClick={() => setNewKeyModal(false)}>Cancel</Btn>
              <Btn onClick={createKey.execute} loading={createKey.loading}>Create Key</Btn>
            </div>
            {createKey.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{createKey.error}</p>}
          </div>
        )}
      </Modal>
    </AdminLayout>
  );
}
