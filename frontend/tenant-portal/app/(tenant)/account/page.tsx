"use client";
import React, { useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Input, Badge, Spinner, Modal, AddBtn, DeleteBtn } from "../../../components/shared/ui";
import { authApi, type UserSession, type ApiKey, type ApiKeyCreated, type MfaSetup, type InviteStaffPayload } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const API_KEYS_ENABLED = false;

export default function AccountPage() {
  const me       = useApi(() => authApi.me(), []);
  const sessions = useApi(() => authApi.getSessions(), []);
  const keys     = useApi(() => API_KEYS_ENABLED
    ? authApi.listApiKeys()
    : Promise.resolve({ keys: [], total: 0 }), []);

  const [tab,  setTab]  = useState<"profile"|"password"|"mfa"|"sessions"|"apikeys"|"team">("profile");
  const [toast, setToast] = useState("");

  // Profile
  const [fullName, setFullName] = useState("");
  React.useEffect(() => { if (me.data) setFullName(me.data.full_name); }, [me.data]);

  // Password
  const [currPass, setCurrPass] = useState("");
  const [newPass,  setNewPass]  = useState("");
  const [confPass, setConfPass] = useState("");

  // MFA
  const [mfaSetup,    setMfaSetup]    = useState<MfaSetup | null>(null);
  const [mfaCode,     setMfaCode]     = useState("");
  const [disableCode, setDisableCode] = useState("");

  // API key creation
  const [keyModal,  setKeyModal]  = useState(false);
  const [keyResult, setKeyResult] = useState<ApiKeyCreated | null>(null);
  const [keyName,   setKeyName]   = useState("");
  const [keyScopes, setKeyScopes] = useState("read");
  const [keyExpiry, setKeyExpiry] = useState("30");

  // Invite staff
  const [inviteModal, setInviteModal] = useState(false);
  const [inv, setInv] = useState<InviteStaffPayload>({ email:"", full_name:"", role:"staff" });

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const updateProfile = useAction(async () => {
    await authApi.updateMe({ full_name: fullName } as never);
    await me.refetch();
    notify("Profile updated.");
  });

  const changePass = useAction(async () => {
    if (newPass !== confPass) { notify("Passwords do not match."); return; }
    await authApi.changePassword(currPass, newPass);
    setCurrPass(""); setNewPass(""); setConfPass("");
    notify("Password changed.");
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
    localStorage.clear();
    window.location.href = "/login";
  });

  const createKey = useAction(async () => {
    const scopes = keyScopes.split(",").map(s => s.trim()).filter(Boolean);
    const result = await authApi.createApiKey(keyName, scopes, parseInt(keyExpiry) || undefined);
    setKeyResult(result);
    setKeyName(""); setKeyScopes("read"); setKeyExpiry("30");
    await keys.refetch();
  });

  const deleteKey = useAction(async (keyId: string) => {
    await authApi.deleteApiKey(keyId);
    await keys.refetch();
    notify("API key deleted.");
  });

  const inviteStaff = useAction(async () => {
    await authApi.inviteStaff(inv);
    setInviteModal(false);
    setInv({ email:"", full_name:"", role:"staff" });
    notify("Invitation sent.");
  });

  const TABS = [
    { id:"profile",  label:"Profile"   },
    { id:"password", label:"Password"  },
    { id:"mfa",      label:"MFA"       },
    { id:"sessions", label:"Sessions"  },
    { id:"team",     label:"Team"      },
  ] as const;

  const u = me.data as (typeof me.data & { mfa_enabled?: boolean }) | null;

  return (
    <TenantLayout activeNav="account">
      <div style={{ display:"flex", flexDirection:"column", gap:24 }}>
        <SectionHeader title="My Account" subtitle="Profile, security and team management" />

        {toast && (
          <div style={{ padding:"10px 16px", background:"var(--success-bg,#d1fae5)", border:"1px solid var(--success,var(--success))",
            borderRadius:"var(--radius-md)", color:"var(--success-text,#065f46)", fontSize:13 }}>
            {toast}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display:"flex", gap:4, borderBottom:"1px solid var(--border)", flexWrap:"wrap" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
              style={{ padding:"8px 14px", border:"none", background:"none", cursor:"pointer",
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
              <div style={{ display:"flex", flexDirection:"column", gap:16, maxWidth:480 }}>
                <Input label="Full Name" value={fullName} onChange={v => setFullName(v)} />
                <Input label="Email" value={u?.email ?? ""} onChange={() => {}} hint="Contact support to change email." />
                <Badge variant="info">{u?.role}</Badge>
                <Btn onClick={updateProfile.execute} loading={updateProfile.loading}>Save Changes</Btn>
              </div>
            )}
          </Card>
        )}

        {/* PASSWORD */}
        {tab === "password" && (
          <Card>
            <div style={{ display:"flex", flexDirection:"column", gap:16, maxWidth:480 }}>
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
                      <p style={{ fontSize:13 }}>Scan this QR code with your authenticator app:</p>
                      <img src={mfaSetup.qr_code_url} alt="MFA QR" style={{ width:180, height:180, border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }} />
                      <p style={{ fontSize:12, color:"var(--text-secondary)" }}>
                        Or enter: <code style={{ background:"var(--surface-alt)", padding:"2px 6px", borderRadius:4 }}>{mfaSetup.secret}</code>
                      </p>
                      <Input label="Verification Code" value={mfaCode} onChange={v => setMfaCode(v)} />
                      <Btn onClick={confirmMfa.execute} loading={confirmMfa.loading}>Confirm & Enable</Btn>
                    </>
                  )}
                  {u?.mfa_enabled && (
                    <>
                      <Input label="Current MFA Code (to disable)" value={disableCode} onChange={v => setDisableCode(v)} />
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
              <Btn variant="danger" size="sm" onClick={logoutAll.execute} loading={logoutAll.loading}>Revoke All</Btn>
            </div>
            {sessions.loading ? <Spinner /> : (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {(sessions.data?.sessions ?? []).map((s: UserSession) => (
                  <div key={s.session_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                    <div>
                      <p style={{ margin:"0 0 2px", fontSize:13, fontWeight:500 }}>
                        {s.ip_address}
                        {s.is_current && <span style={{ marginLeft:8 }}><Badge variant="success">Current</Badge></span>}
                      </p>
                      <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                        Last: {new Date(s.last_seen_at).toLocaleString()} · Expires: {new Date(s.expires_at).toLocaleString()}
                      </p>
                    </div>
                    {!s.is_current && (
                      <Btn variant="ghost" size="sm" onClick={() => revokeSession.execute(s.session_id)} loading={revokeSession.loading}>
                        Revoke
                      </Btn>
                    )}
                  </div>
                ))}
                {(sessions.data?.sessions ?? []).length === 0 && (
                  <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>No sessions found.</p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* API KEYS */}
        {tab === "apikeys" && (
          <Card>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <p style={{ fontWeight:600, margin:0 }}>API Keys</p>
              <AddBtn label="New Key" onClick={() => setKeyModal(true)}/>
            </div>
            {keys.loading ? <Spinner /> : (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {(keys.data?.keys ?? []).map((k: ApiKey) => (
                  <div key={k.key_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"12px 14px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)" }}>
                    <div>
                      <div style={{ display:"flex", gap:8, marginBottom:4 }}>
                        <span style={{ fontWeight:600, fontSize:13 }}>{k.name}</span>
                        <Badge variant={k.is_active ? "success" : "muted"}>{k.is_active ? "Active" : "Inactive"}</Badge>
                      </div>
                      <p style={{ margin:0, fontSize:11, color:"var(--text-secondary)" }}>
                        {k.prefix}••••  ·  {k.scopes.join(", ")}
                        {k.expires_at && `  ·  Expires ${new Date(k.expires_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    <DeleteBtn onClick={() => deleteKey.execute(k.key_id)}/>
                  </div>
                ))}
                {(keys.data?.keys ?? []).length === 0 && (
                  <p style={{ color:"var(--text-secondary)", fontSize:13, textAlign:"center", padding:24 }}>No API keys yet.</p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* TEAM */}
        {tab === "team" && (
          <Card>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <p style={{ fontWeight:600, margin:0 }}>Team Invitations</p>
              <AddBtn label="Invite Member" onClick={() => setInviteModal(true)}/>
            </div>
            <p style={{ color:"var(--text-secondary)", fontSize:13 }}>
              Invite staff members to your tenant. They will receive an email with a link to set up their account.
            </p>
          </Card>
        )}
      </div>

      {/* New API Key Modal */}
      <Modal open={keyModal} onClose={() => { setKeyModal(false); setKeyResult(null); }} title="Create API Key" size="md">
        {keyResult ? (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ padding:12, background:"var(--success-bg,#d1fae5)", borderRadius:"var(--radius-md)", border:"1px solid var(--success,var(--success))" }}>
              <p style={{ margin:"0 0 8px", fontWeight:600 }}>Key Created — copy it now!</p>
              <code style={{ display:"block", wordBreak:"break-all", fontSize:12, padding:"8px 10px",
                background:"white", border:"1px solid var(--border)", borderRadius:6 }}>
                {keyResult.secret_key}
              </code>
            </div>
            <Btn onClick={() => { setKeyModal(false); setKeyResult(null); }}>Done</Btn>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Name" value={keyName} onChange={v => setKeyName(v)} />
            <Input label="Scopes (comma-separated)" value={keyScopes} onChange={v => setKeyScopes(v)} />
            <Input label="Expires in days" value={keyExpiry} onChange={v => setKeyExpiry(v)} />
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <Btn variant="ghost" onClick={() => setKeyModal(false)}>Cancel</Btn>
              <Btn onClick={createKey.execute} loading={createKey.loading}>Create</Btn>
            </div>
          </div>
        )}
      </Modal>

      {/* Invite Modal */}
      <Modal open={inviteModal} onClose={() => setInviteModal(false)} title="Invite Team Member" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Input label="Full Name" value={inv.full_name} onChange={v => setInv(p => ({ ...p, full_name: v }))} />
          <Input label="Email" value={inv.email} onChange={v => setInv(p => ({ ...p, email: v }))} />
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>Role</label>
            <select value={inv.role} onChange={e => setInv(p => ({ ...p, role: e.target.value }))}
              style={{ width:"100%", padding:"8px 10px", border:"1px solid var(--border)", borderRadius:"var(--radius-md)",
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13 }}>
              <option value="staff">Staff</option>
              <option value="manager">Manager</option>
            </select>
          </div>
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={() => setInviteModal(false)}>Cancel</Btn>
            <Btn onClick={inviteStaff.execute} loading={inviteStaff.loading}>Send Invite</Btn>
          </div>
          {inviteStaff.error && <p style={{ color:"var(--danger)", fontSize:12 }}>{inviteStaff.error}</p>}
        </div>
      </Modal>
    </TenantLayout>
  );
}
