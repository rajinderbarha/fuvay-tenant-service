"use client";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Input, Skeleton } from "../../../../components/shared/ui";
import {
  providerTeamMembersApi, providerOnboardingApi, categoryDashboardApi,
  type ProviderTeamMember, type ProviderTeamMemberPayload, type MemberType,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Users, AlertCircle, UserPlus, Trash2, Edit2, Key, Eye, EyeOff } from "lucide-react";

async function tryOnboardingRefresh() {
  try { await providerOnboardingApi.refresh(); } catch (e) { console.warn("Onboarding refresh failed", e); }
}

// ── Category-aware labels ─────────────────────────────────────────────────────

function pageTitle(categoryType: string | null): string {
  if (categoryType === "home_services") return "Technicians";
  if (categoryType === "coaching" || categoryType === "coaching_ielts") return "Trainers & Counsellors";
  if (categoryType === "real_estate") return "Agents";
  return "Team Members";
}

function memberTypeOptions(categoryType: string | null): { value: MemberType; label: string }[] {
  if (categoryType === "home_services") return [
    { value: "technician", label: "Technician" },
    { value: "staff",      label: "Staff" },
    { value: "manager",    label: "Manager" },
  ];
  if (categoryType === "coaching" || categoryType === "coaching_ielts") return [
    { value: "trainer",    label: "Trainer" },
    { value: "counsellor", label: "Counsellor" },
    { value: "staff",      label: "Staff" },
    { value: "manager",    label: "Manager" },
  ];
  if (categoryType === "real_estate") return [
    { value: "agent",   label: "Agent" },
    { value: "staff",   label: "Staff" },
    { value: "manager", label: "Manager" },
  ];
  return [
    { value: "staff",   label: "Staff" },
    { value: "manager", label: "Manager" },
  ];
}

// ── Credentials Modal (shown once after create-login) ─────────────────────────

function CredentialsModal({
  open, credentials, onClose,
}: {
  open: boolean;
  credentials: { username: string; password: string } | null;
  onClose: () => void;
}) {
  const [revealed, setRevealed] = useState(false);
  if (!open || !credentials) return null;
  return (
    <Modal open title="Login Credentials Created" onClose={onClose} size="sm">
      <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
        <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(220,38,38,0.08)",
          border:"1px solid rgba(220,38,38,0.25)" }}>
          <p style={{ fontSize:13, fontWeight:700, color:"#dc2626", margin:"0 0 4px" }}>
            ⚠ Save these credentials now.
          </p>
          <p style={{ fontSize:12, color:"#dc2626", margin:0 }}>
            They will not be shown again after you close this window.
          </p>
        </div>
        <div style={{ background:"var(--surface-sunken)", borderRadius:10, padding:"12px 16px",
          border:"1px solid var(--border)" }}>
          <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)", margin:"0 0 8px",
            textTransform:"uppercase", letterSpacing:"0.06em" }}>Username</p>
          <p style={{ fontSize:14, fontFamily:"monospace", color:"var(--text-primary)", margin:0 }}>
            {credentials.username}
          </p>
        </div>
        <div style={{ background:"var(--surface-sunken)", borderRadius:10, padding:"12px 16px",
          border:"1px solid var(--border)" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
            <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)", margin:0,
              textTransform:"uppercase", letterSpacing:"0.06em" }}>Password</p>
            <button onClick={() => setRevealed(r => !r)}
              style={{ background:"none", border:"none", cursor:"pointer", color:"var(--text-secondary)",
                display:"flex", alignItems:"center", gap:4, fontSize:11 }}>
              {revealed ? <EyeOff size={13}/> : <Eye size={13}/>}
              {revealed ? "Hide" : "Reveal"}
            </button>
          </div>
          <p style={{ fontSize:14, fontFamily:"monospace", color:"var(--text-primary)", margin:0,
            filter: revealed ? "none" : "blur(5px)", userSelect: revealed ? "auto" : "none",
            transition:"filter 0.2s" }}>
            {credentials.password}
          </p>
        </div>
        <Btn variant="primary" size="sm" onClick={onClose}>I have saved these credentials</Btn>
      </div>
    </Modal>
  );
}

// ── Add/Edit Member Modal ─────────────────────────────────────────────────────

const BLANK_MEMBER: ProviderTeamMemberPayload = {
  member_type: "staff",
  full_name: "",
  phone: "",
  email: "",
  designation: "",
  skills: null,
  supported_offering_ids: null,
  supported_type_ids: null,
  supported_brand_ids: null,
  service_area_ids: null,
  can_receive_assignment: true,
  profile_photo_url: null,
  create_login: false,
};

interface MemberFormProps {
  open: boolean;
  existing: ProviderTeamMember | null;
  categoryType: string | null;
  onClose: () => void;
  onSaved: (credentials?: { username: string; password: string } | null) => void;
}

function MemberModal({ open, existing, categoryType, onClose, onSaved }: MemberFormProps) {
  const isEdit = !!existing;
  const typeOptions = memberTypeOptions(categoryType);
  const [form, setForm] = useState<ProviderTeamMemberPayload>({ ...BLANK_MEMBER, member_type: typeOptions[0]?.value ?? "staff" });
  const [skillsText, setSkillsText] = useState("");

  React.useEffect(() => {
    if (!open) return;
    if (existing) {
      setForm({
        member_type: existing.member_type,
        full_name: existing.full_name,
        phone: existing.phone ?? "",
        email: existing.email ?? "",
        designation: existing.designation ?? "",
        skills: existing.skills,
        supported_offering_ids: existing.supported_offering_ids,
        supported_type_ids: existing.supported_type_ids,
        supported_brand_ids: existing.supported_brand_ids,
        service_area_ids: existing.service_area_ids,
        can_receive_assignment: existing.can_receive_assignment,
        profile_photo_url: existing.profile_photo_url,
        create_login: false,
      });
      setSkillsText((existing.skills ?? []).join(", "));
    } else {
      setForm({ ...BLANK_MEMBER, member_type: typeOptions[0]?.value ?? "staff" });
      setSkillsText("");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, existing]);

  const saveAction = useAction(useCallback(async () => {
    const skills = skillsText.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);
    const payload = { ...form, skills: skills.length ? skills : null };
    if (isEdit && existing) {
      await providerTeamMembersApi.update(existing.member_id, payload);
      onSaved(null);
    } else {
      const res = await providerTeamMembersApi.create(payload);
      onSaved(res.credentials ?? null);
    }
    onClose();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, skillsText, isEdit, existing]));

  const f = (key: keyof ProviderTeamMemberPayload, val: unknown) =>
    setForm(prev => ({ ...prev, [key]: val }));

  if (!open) return null;

  return (
    <Modal open title={isEdit ? `Edit: ${existing?.full_name}` : "Add Team Member"}
      onClose={onClose} size="md">
      <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
        {saveAction.error && (
          <div style={{ padding:"10px 14px", borderRadius:9, background:"rgba(220,38,38,0.08)",
            border:"1px solid rgba(220,38,38,0.25)" }}>
            <p style={{ fontSize:12, color:"#dc2626", margin:0 }}>{saveAction.error}</p>
          </div>
        )}

        {/* Member type */}
        <div>
          <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
            marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            Member Type
          </label>
          <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
            {typeOptions.map(opt => (
              <button key={opt.value} onClick={() => f("member_type", opt.value)}
                style={{ padding:"6px 12px", borderRadius:8, border:"1px solid", cursor:"pointer", fontSize:12,
                  borderColor: form.member_type===opt.value ? "var(--brand)" : "var(--border)",
                  background: form.member_type===opt.value ? "rgba(37,99,235,0.08)" : "var(--surface)",
                  color: form.member_type===opt.value ? "var(--brand)" : "var(--text-secondary)",
                  fontWeight: form.member_type===opt.value ? 700 : 400 }}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Basic info */}
        <Input label="Full Name" placeholder="Aman Singh" value={form.full_name}
          onChange={v => f("full_name", v)} required/>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
          <Input label="Phone" placeholder="+91 98xxx xxxxx" value={form.phone ?? ""}
            onChange={v => f("phone", v)}/>
          <Input label="Email" type="email" placeholder="aman@example.com" value={form.email ?? ""}
            onChange={v => f("email", v)}/>
        </div>

        <Input label="Designation" placeholder="Senior Technician, Lead Trainer…" value={form.designation ?? ""}
          onChange={v => f("designation", v)}/>

        <div>
          <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
            marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            Skills (comma separated)
          </label>
          <input value={skillsText} onChange={e => setSkillsText(e.target.value)}
            placeholder="AC Repair, Split AC, Daikin, Inverter"
            style={{ width:"100%", fontSize:13, padding:"8px 10px", borderRadius:8,
              border:"1px solid var(--border)", background:"var(--surface)", color:"var(--text-primary)",
              outline:"none", boxSizing:"border-box" }}/>
        </div>

        {/* Flags */}
        <div style={{ display:"flex", gap:16, flexWrap:"wrap" }}>
          <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer", userSelect:"none" }}>
            <input type="checkbox" checked={form.can_receive_assignment ?? true}
              onChange={e => f("can_receive_assignment", e.target.checked)}
              style={{ width:15, height:15 }}/>
            <span style={{ fontSize:13, color:"var(--text-primary)" }}>Can receive job assignments</span>
          </label>
          {!isEdit && (
            <label style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer", userSelect:"none" }}>
              <input type="checkbox" checked={form.create_login ?? false}
                onChange={e => f("create_login", e.target.checked)}
                style={{ width:15, height:15 }}/>
              <span style={{ fontSize:13, color:"var(--text-primary)" }}>Create login account</span>
            </label>
          )}
        </div>

        <div style={{ display:"flex", gap:8, justifyContent:"flex-end", paddingTop:4 }}>
          <Btn size="sm" variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn size="sm" variant="primary" loading={saveAction.loading}
            disabled={!form.full_name.trim()}
            onClick={() => saveAction.execute()}>
            {isEdit ? "Save Changes" : "Add Member"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TeamMembersPage() {
  const runtime = useApi(useCallback(() => categoryDashboardApi.getRuntime(), []));
  const members = useApi(useCallback(() => providerTeamMembersApi.list(), []));
  const [modalOpen,   setModalOpen]   = useState(false);
  const [editMember,  setEditMember]  = useState<ProviderTeamMember | null>(null);
  const [credentials, setCredentials] = useState<{ username: string; password: string } | null>(null);
  const [toast,    setToast]    = useState<string | null>(null);
  const [toastErr, setToastErr] = useState<string | null>(null);

  const categoryType: string | null = runtime.data?.tenant?.category?.category_type ?? null;
  const title = pageTitle(categoryType);

  function flash(msg: string, err = false) {
    if (err) { setToastErr(msg); setTimeout(() => setToastErr(null), 4000); }
    else     { setToast(msg);    setTimeout(() => setToast(null), 3000); }
  }

  const deactivateAction = useAction(useCallback(async (id: string) => {
    await providerTeamMembersApi.deactivate(id);
    members.refetch();
    await tryOnboardingRefresh();
    flash("Member deactivated.");
  }, [members]));

  const activateAction = useAction(useCallback(async (id: string) => {
    await providerTeamMembersApi.activate(id);
    members.refetch();
    flash("Member activated.");
  }, [members]));

  const createLoginAction = useAction(useCallback(async (id: string) => {
    const res = await providerTeamMembersApi.createLogin(id);
    if (res.credentials) setCredentials(res.credentials);
    else flash("Login already exists or could not be created.");
  }, []));

  function handleSaved(creds?: { username: string; password: string } | null) {
    members.refetch();
    tryOnboardingRefresh();
    setModalOpen(false);
    setEditMember(null);
    if (creds) { setCredentials(creds); flash("Member added."); }
    else flash(editMember ? "Member updated." : "Member added.");
  }

  const list: ProviderTeamMember[] = members.data?.members ?? [];
  const activeCount = list.filter(m => m.status === "active").length;
  const typeOptions = memberTypeOptions(categoryType);

  return (
    <TenantLayout activeNav="provider-team-members">
      {/* Header */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
        marginBottom:20, flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
            {title}
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Manage the people who deliver your services.
          </p>
        </div>
        <Btn variant="primary" size="sm" onClick={() => { setEditMember(null); setModalOpen(true); }}>
          <UserPlus size={14}/> Add Member
        </Btn>
      </div>

      {/* Toasts */}
      {toast    && <div style={{ padding:"10px 16px", borderRadius:10, marginBottom:12,
        background:"rgba(5,150,105,0.08)", border:"1px solid rgba(5,150,105,0.25)",
        fontSize:13, color:"#059669" }}>✓ {toast}</div>}
      {toastErr && <div style={{ padding:"10px 16px", borderRadius:10, marginBottom:12,
        background:"rgba(220,38,38,0.08)", border:"1px solid rgba(220,38,38,0.25)",
        fontSize:13, color:"#dc2626" }}>✕ {toastErr}</div>}

      {/* Summary */}
      {!members.loading && list.length > 0 && (
        <div style={{ display:"flex", gap:10, marginBottom:16 }}>
          <div style={{ padding:"10px 16px", borderRadius:10, background:"var(--surface-sunken)",
            border:"1px solid var(--border)", fontSize:12 }}>
            <span style={{ fontWeight:700, color:"var(--text-primary)" }}>{list.length}</span>
            <span style={{ color:"var(--text-secondary)", marginLeft:4 }}>total</span>
          </div>
          <div style={{ padding:"10px 16px", borderRadius:10, background:"rgba(5,150,105,0.06)",
            border:"1px solid rgba(5,150,105,0.2)", fontSize:12 }}>
            <span style={{ fontWeight:700, color:"#059669" }}>{activeCount}</span>
            <span style={{ color:"var(--text-secondary)", marginLeft:4 }}>active</span>
          </div>
        </div>
      )}

      {/* Content */}
      {members.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={64}/>)}
        </div>
      ) : members.error ? (
        <Card>
          <div style={{ textAlign:"center", padding:"32px 0" }}>
            <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
            <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{members.error}</p>
            <Btn size="sm" variant="primary" onClick={members.refetch}>Retry</Btn>
          </div>
        </Card>
      ) : list.length === 0 ? (
        <Card style={{ textAlign:"center" }}>
          <Users size={32} style={{ color:"var(--text-tertiary)", display:"block", margin:"0 auto 12px" }}/>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:"0 0 12px" }}>No {title.toLowerCase()} yet.</p>
          <Btn size="sm" variant="primary" onClick={() => { setEditMember(null); setModalOpen(true); }}>
            Add First Member
          </Btn>
        </Card>
      ) : (
        <Card padding={0}>
          <div style={{ overflowX:"auto" }}>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Name","Type","Phone","Email","Designation","Skills","Assignments","Status","Actions"].map(h => (
                    <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                      whiteSpace:"nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((m, i) => {
                  const typeLabel = typeOptions.find(t => t.value === m.member_type)?.label ?? m.member_type;
                  return (
                    <tr key={m.member_id}
                      style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"10px 12px" }}>
                        <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                          {m.full_name}
                        </p>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <Badge variant="muted" size="sm">{typeLabel}</Badge>
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                        {m.phone ?? "—"}
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                        {m.email ?? "—"}
                      </td>
                      <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                        {m.designation ?? "—"}
                      </td>
                      <td style={{ padding:"10px 12px", maxWidth:140 }}>
                        {m.skills && m.skills.length > 0 ? (
                          <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                            {m.skills.slice(0,3).map(s => (
                              <span key={s} style={{ fontSize:10, padding:"2px 6px", borderRadius:4,
                                background:"var(--surface-sunken)", border:"1px solid var(--border)",
                                color:"var(--text-secondary)" }}>{s}</span>
                            ))}
                            {m.skills.length > 3 && (
                              <span style={{ fontSize:10, color:"var(--text-tertiary)" }}>+{m.skills.length-3}</span>
                            )}
                          </div>
                        ) : <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>—</span>}
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <Badge variant={m.can_receive_assignment ? "success" : "muted"} size="sm">
                          {m.can_receive_assignment ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <Badge variant={m.status === "active" ? "success" : "muted"} size="sm">
                          {m.status}
                        </Badge>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                          <Btn size="xs" variant="ghost" onClick={() => {
                            setEditMember(m); setModalOpen(true);
                          }}>
                            <Edit2 size={11}/>
                          </Btn>
                          {m.status === "active" ? (
                            <Btn size="xs" variant="ghost" loading={deactivateAction.loading}
                              onClick={() => {
                                if (confirm(`Deactivate ${m.full_name}?`)) deactivateAction.execute(m.member_id);
                              }}>
                              Deactivate
                            </Btn>
                          ) : (
                            <Btn size="xs" variant="ghost" loading={activateAction.loading}
                              onClick={() => activateAction.execute(m.member_id)}>
                              Activate
                            </Btn>
                          )}
                          <Btn size="xs" variant="ghost"
                            loading={createLoginAction.loading}
                            onClick={() => {
                              if (confirm(`Create login for ${m.full_name}? Credentials will be shown once.`))
                                createLoginAction.execute(m.member_id);
                            }}>
                            <Key size={11}/>
                          </Btn>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Add/Edit Modal */}
      <MemberModal
        open={modalOpen}
        existing={editMember}
        categoryType={categoryType}
        onClose={() => { setModalOpen(false); setEditMember(null); }}
        onSaved={handleSaved}
      />

      {/* Credentials Modal */}
      <CredentialsModal
        open={!!credentials}
        credentials={credentials}
        onClose={() => setCredentials(null)}
      />
    </TenantLayout>
  );
}
