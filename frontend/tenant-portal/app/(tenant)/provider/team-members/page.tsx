"use client";
import React, { useCallback, useMemo, useState } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  providerTeamMembersApi, providerOnboardingApi, categoryDashboardApi,
  providerOfferingsApi, providerServiceAreasApi, mediaAssetApi,
  type ProviderTeamMember, type ProviderTeamMemberPayload, type MemberType,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { Users, AlertCircle, UserPlus, Edit2, Key, Eye, EyeOff, ChevronDown, CheckCircle2, XCircle, Camera } from "lucide-react";
import { PageHeader, Card, Button, Modal, Input, Skeleton, StatusBadge as DsStatusBadge, Alert } from "@serviceos/design-system";
import { DefaultAvatar, resolveMediaUrl } from "../../../../components/shared/ProfilePhotoUploader";
import { Select as LocalSelect } from "../../../../components/shared/ui";

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

// Role/Designation is a provider-selected dropdown, not free text — kept
// category-aware like memberTypeOptions above. Home Services gets a real
// list of field-service designations; other verticals get a small sane
// fallback rather than fabricating designations for verticals not in scope.
function designationOptions(categoryType: string | null): string[] {
  if (categoryType === "home_services") return [
    "Technician", "Senior Technician", "Lead Technician", "Trainee Technician",
    "Electrician", "Plumber", "AC Technician", "Appliance Repair Technician",
    "Carpenter", "Painter", "Pest Control Technician", "Cleaner",
    "Installation Specialist", "Field Supervisor", "Team Lead",
    "Operations Manager", "Customer Support Executive",
  ];
  if (categoryType === "coaching" || categoryType === "coaching_ielts") return [
    "Trainer", "Senior Trainer", "Counsellor", "Academic Coordinator", "Center Manager",
  ];
  if (categoryType === "real_estate") return [
    "Sales Agent", "Senior Agent", "Property Consultant", "Branch Manager",
  ];
  return ["Staff Member", "Team Lead", "Manager"];
}

// Skills are provider-selected chips, not free text — category-aware for
// the same reason as designations above.
function skillOptions(categoryType: string | null): string[] {
  if (categoryType === "home_services") return [
    "AC Repair", "AC Installation", "AC Maintenance", "Refrigerator Repair",
    "Washing Machine Repair", "Water Heater Repair", "Plumbing Repair",
    "Electrical Wiring", "Appliance Repair", "Carpentry", "Painting",
    "Pest Control", "Deep Cleaning", "Furniture Assembly", "CCTV Installation",
    "Inverter & Battery Service", "RO Water Purifier Service",
  ];
  return [];
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
    <Modal open title="Login Credentials Created" onClose={onClose}
      footer={<Button variant="primary" size="sm" onClick={onClose}>I have saved these credentials</Button>}>
      <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
        <Alert tone="danger" title="Save these credentials now.">
          They will not be shown again after you close this window.
        </Alert>
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

// ── Small reusable pieces (no shared component exists yet for these) ──────────

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      style={{
        width: 36, height: 20, borderRadius: 999, border: "none", cursor: "pointer", flexShrink: 0,
        background: checked ? "var(--brand)" : "var(--border)", position: "relative", transition: "background 0.15s",
      }}>
      <span style={{
        position: "absolute", top: 2, left: checked ? 18 : 2, width: 16, height: 16, borderRadius: "50%",
        background: "#fff", transition: "left 0.15s", boxShadow: "var(--shadow-sm)",
      }}/>
    </button>
  );
}

function ToggleRow({ label, helper, checked, onChange }: { label: string; helper: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12,
      padding: "10px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <div>
        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{label}</p>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{helper}</p>
      </div>
      <Toggle checked={checked} onChange={onChange}/>
    </div>
  );
}

function ChipMultiSelect({ options, selected, onToggle, emptyText }: {
  options: { id: string; label: string }[]; selected: string[]; onToggle: (id: string) => void; emptyText: string;
}) {
  if (options.length === 0) return <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{emptyText}</p>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {options.map(o => {
        const active = selected.includes(o.id);
        return (
          <button key={o.id} type="button" onClick={() => onToggle(o.id)} style={{
            padding: "5px 12px", borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
            border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
            background: active ? "var(--accent-muted)" : "var(--surface)",
            color: active ? "var(--brand)" : "var(--text-secondary)",
          }}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

const WIZARD_STEPS = ["Basic Info", "Role & Services", "Work Area & Access", "Review & Create"];

function Stepper({ step }: { step: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
      <div style={{ display: "flex", alignItems: "center", flex: 1 }}>
        {WIZARD_STEPS.map((label, i) => {
          const done = i < step;
          const current = i === step;
          return (
            <React.Fragment key={label}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <span aria-hidden="true" style={{
                  width: 24, height: 24, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, fontWeight: 700, flexShrink: 0,
                  background: done ? "var(--brand)" : current ? "var(--accent-muted)" : "var(--surface-sunken)",
                  color: done ? "var(--text-on-brand)" : current ? "var(--brand)" : "var(--text-tertiary)",
                  border: current ? "1px solid var(--brand)" : "1px solid var(--border)",
                }}>
                  {done ? <CheckCircle2 size={13}/> : i + 1}
                </span>
                <span style={{ fontSize: 12, fontWeight: current ? 700 : 500, whiteSpace: "nowrap",
                  color: current ? "var(--text-primary)" : done ? "var(--text-secondary)" : "var(--text-tertiary)" }}>
                  {label}
                </span>
              </div>
              {i < WIZARD_STEPS.length - 1 && (
                <span aria-hidden="true" style={{ flex: 1, height: 2, margin: "0 10px", minWidth: 16,
                  background: i < step ? "var(--brand)" : "var(--border)" }}/>
              )}
            </React.Fragment>
          );
        })}
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)", flexShrink: 0, marginLeft: 16, whiteSpace: "nowrap" }}>
        Step {step + 1} of {WIZARD_STEPS.length}
      </span>
    </div>
  );
}

function SummaryBlock({ title, onEdit, children }: { title: string; onEdit: () => void; children: React.ReactNode }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{title}</p>
        <button type="button" onClick={onEdit} style={{ display: "flex", alignItems: "center", gap: 4,
          background: "none", border: "none", cursor: "pointer", color: "var(--brand)", fontSize: 12, fontWeight: 600, fontFamily: "inherit" }}>
          <Edit2 size={11}/> Edit
        </button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}

function AccordionSection({ title, subtitle, open, onToggle, children }: {
  title: string; subtitle: string; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
      <button type="button" onClick={onToggle} style={{
        width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
        padding: "10px 12px", background: "var(--surface-sunken)", border: "none", cursor: "pointer", fontFamily: "inherit",
      }}>
        <div style={{ textAlign: "left" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{title}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "1px 0 0" }}>{subtitle}</p>
        </div>
        <ChevronDown size={16} style={{ color: "var(--text-tertiary)", flexShrink: 0, transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}/>
      </button>
      {open && <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>{children}</div>}
    </div>
  );
}

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
  const designations = designationOptions(categoryType);
  const skillChoices = skillOptions(categoryType);
  const [form, setForm] = useState<ProviderTeamMemberPayload>({ ...BLANK_MEMBER, member_type: typeOptions[0]?.value ?? "staff" });
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const pendingPhotoFile = React.useRef<File | null>(null);
  const photoInputRef = React.useRef<HTMLInputElement>(null);

  // Real data only -- "Assigned Services" is wired to the tenant's actual
  // enabled offerings (supported_offering_ids), and "Work Area" to the
  // tenant's actual configured service areas (service_area_ids). Both are
  // real ProviderTeamMemberPayload fields that the old form never exposed.
  const offerings = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []), []);
  const areas = useApi(useCallback(() => providerServiceAreasApi.list(), []), []);
  const offeringOptions = useMemo(() =>
    (offerings.data?.offerings ?? []).map(o => ({ id: o.offering_id, label: o.provider_display_name || o.offering_name })),
    [offerings.data]);
  // Only show areas where the provider actually configured a real city or
  // zipcode -- "zone"/"radius" coverage entries have no such value and were
  // previously falling back to a placeholder "Area" label, which isn't a
  // real location the provider services.
  const areaOptions = useMemo(() =>
    (areas.data?.areas ?? [])
      .filter(a => (a.coverage_type === "city" && a.city) || (a.coverage_type === "zipcode" && a.zipcode))
      .map(a => ({ id: a.id, label: a.coverage_type === "zipcode" ? (a.zipcode as string) : (a.city as string) })),
    [areas.data]);

  React.useEffect(() => {
    if (!open) return;
    setPhotoError(null);
    setStep(0);
    pendingPhotoFile.current = null;
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
      setSelectedSkills(existing.skills ?? []);
      setPhotoPreview(resolveMediaUrl(existing.profile_photo_url));
    } else {
      setForm({ ...BLANK_MEMBER, member_type: typeOptions[0]?.value ?? "staff" });
      setSelectedSkills([]);
      setPhotoPreview(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, existing]);

  // Photo upload uses the generic media endpoint (owner_type/owner_id are
  // freeform on the backend, unlike the fixed OwnerType union the shared
  // ProfilePhotoUploader component expects, which is why this is wired
  // directly here instead of reusing that component). In edit mode the
  // member already has an id, so the file uploads immediately. In add mode
  // there's no member_id yet, so the file is held and uploaded right after
  // create() succeeds, then attached via a lightweight partial update.
  async function handlePhotoSelect(file: File) {
    setPhotoError(null);
    const localUrl = URL.createObjectURL(file);
    setPhotoPreview(localUrl);
    if (isEdit && existing) {
      setPhotoUploading(true);
      try {
        const asset = await mediaAssetApi.upload("team_member_photo", "team_member", existing.member_id, file);
        const url = resolveMediaUrl(asset.preview_url ?? asset.public_url);
        f("profile_photo_url", url);
        setPhotoPreview(url);
      } catch (e: unknown) {
        setPhotoError(e instanceof Error ? e.message : "Photo upload failed.");
        setPhotoPreview(resolveMediaUrl(existing.profile_photo_url));
      } finally {
        setPhotoUploading(false);
      }
    } else {
      pendingPhotoFile.current = file;
    }
  }

  const saveAction = useAction(useCallback(async () => {
    const payload = { ...form, skills: selectedSkills.length ? selectedSkills : null };
    if (isEdit && existing) {
      await providerTeamMembersApi.update(existing.member_id, payload);
      onSaved(null);
    } else {
      const res = await providerTeamMembersApi.create(payload);
      const newId = res.member.member_id;
      if (pendingPhotoFile.current) {
        try {
          const asset = await mediaAssetApi.upload("team_member_photo", "team_member", newId, pendingPhotoFile.current);
          const url = resolveMediaUrl(asset.preview_url ?? asset.public_url);
          await providerTeamMembersApi.update(newId, { profile_photo_url: url });
        } catch {
          // Member was created successfully; photo upload failing shouldn't
          // block the whole flow -- it can be added later from Edit.
        }
      }
      onSaved(res.credentials ?? null);
    }
    onClose();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, selectedSkills, isEdit, existing]));

  const f = (key: keyof ProviderTeamMemberPayload, val: unknown) =>
    setForm(prev => ({ ...prev, [key]: val }));

  const toggleOffering = (id: string) => {
    const cur = form.supported_offering_ids ?? [];
    f("supported_offering_ids", cur.includes(id) ? cur.filter(x => x !== id) : [...cur, id]);
  };
  const toggleArea = (id: string) => {
    const cur = form.service_area_ids ?? [];
    f("service_area_ids", cur.includes(id) ? cur.filter(x => x !== id) : [...cur, id]);
  };
  const toggleSkill = (skill: string) => {
    setSelectedSkills(cur => cur.includes(skill) ? cur.filter(x => x !== skill) : [...cur, skill]);
  };

  if (!open) return null;

  const selectedServiceLabels = offeringOptions.filter(o => (form.supported_offering_ids ?? []).includes(o.id)).map(o => o.label);
  const selectedAreaLabels = areaOptions.filter(a => (form.service_area_ids ?? []).includes(a.id)).map(a => a.label);
  const typeLabel = typeOptions.find(t => t.value === form.member_type)?.label ?? form.member_type;

  // Step-based validation -- required fields are distributed across steps
  // rather than all validated at once, and Continue/Create stay disabled
  // until the current step's requirements are met.
  const step0Valid = form.full_name.trim() && (form.phone ?? "").trim() && (form.email ?? "").trim();
  const step1Valid = (form.designation ?? "").trim().length > 0;
  const canContinue = step === 0 ? step0Valid : step === 1 ? step1Valid : true;
  const isLastStep = step === WIZARD_STEPS.length - 1;

  const avatarPicker = (
    <div style={{ position: "relative", width: 96, height: 96, flexShrink: 0 }}>
      <button type="button" onClick={() => photoInputRef.current?.click()} disabled={photoUploading}
        style={{ display: "flex", width: 96, height: 96, borderRadius: "var(--radius-lg)", padding: 0,
          cursor: photoUploading ? "default" : "pointer", position: "relative", overflow: "hidden",
          alignItems: "center", justifyContent: "center",
          border: photoPreview ? "2px solid var(--border)" : "2px dashed var(--border)",
          background: photoPreview ? "transparent" : "var(--surface-sunken)" }}
        aria-label="Upload profile photo">
        {photoPreview ? (
          <img src={photoPreview} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }}/>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, color: "var(--text-tertiary)" }}>
            <Camera size={20}/>
            <span style={{ fontSize: 10, fontWeight: 600, textAlign: "center", lineHeight: 1.2 }}>Upload<br/>Photo</span>
          </div>
        )}
        <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
          background: "rgba(0,0,0,0.5)", opacity: 0, transition: "opacity 0.15s" }}
          className="team-photo-overlay">
          <Camera size={20} color="#fff"/>
        </span>
      </button>
      {photoUploading && (
        <span style={{ position: "absolute", inset: 0, borderRadius: "var(--radius-lg)", display: "flex",
          alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)" }}>
          <span style={{ width: 18, height: 18, border: "2px solid #fff", borderTopColor: "transparent",
            borderRadius: "50%", animation: "spin 0.8s linear infinite" }}/>
        </span>
      )}
      <input ref={photoInputRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: "none" }}
        onChange={e => { const file = e.target.files?.[0]; if (file) handlePhotoSelect(file); e.target.value = ""; }}/>
      <style>{`
        button[aria-label="Upload profile photo"]:hover .team-photo-overlay { opacity: 1; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );

  return (
    <Modal open title={isEdit ? `Edit: ${existing?.full_name}` : "Add Team Member"}
      onClose={onClose}
      footer={<>
        <Button size="sm" variant="secondary" onClick={onClose}>Cancel</Button>
        {step > 0 && (
          <Button size="sm" variant="secondary" onClick={() => setStep(s => s - 1)}>Back</Button>
        )}
        {isLastStep ? (
          <Button size="sm" variant="primary" loading={saveAction.loading}
            disabled={!step0Valid}
            onClick={() => saveAction.execute()}>
            {isEdit ? "Save Changes" : "Create Member"}
          </Button>
        ) : (
          <Button size="sm" variant="primary" disabled={!canContinue} onClick={() => setStep(s => s + 1)}>
            Continue
          </Button>
        )}
      </>}>
      <div style={{ width: "min(880px, 90vw)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "-6px 0 16px" }}>
          {isEdit ? `Update ${existing?.full_name}'s details` : "Create staff, technician or manager in a guided flow"}
        </p>

        <Stepper step={step}/>

        {saveAction.error && <div style={{ margin: "14px 0 0" }}><Alert tone="danger">{saveAction.error}</Alert></div>}
        {photoError && <div style={{ margin: "14px 0 0" }}><Alert tone="danger">{photoError}</Alert></div>}

        <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap", marginTop: 18 }}>
          {/* Left: current step */}
          <div style={{ flex: "1 1 460px", minWidth: 320, display: "flex", flexDirection: "column", gap: 14 }}>

            {/* ── Step 1: Basic Info ── */}
            {step === 0 && (
              <>
                <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                  {avatarPicker}
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", display: "block",
                      marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Member Type
                    </label>
                    <div style={{ display: "flex", gap: 4, padding: 3, background: "var(--surface-sunken)",
                      borderRadius: "var(--radius-md)", border: "1px solid var(--border)", width: "fit-content" }}>
                      {typeOptions.map(opt => (
                        <button key={opt.value} type="button" onClick={() => f("member_type", opt.value)} style={{
                          padding: "5px 12px", borderRadius: 7, fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
                          border: "none", background: form.member_type === opt.value ? "var(--surface)" : "transparent",
                          color: form.member_type === opt.value ? "var(--text-primary)" : "var(--text-secondary)",
                          boxShadow: form.member_type === opt.value ? "var(--shadow-sm)" : "none",
                        }}>
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <Input label="Full Name" placeholder="Aman Singh" value={form.full_name}
                  onChange={e => f("full_name", e.target.value)} required/>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <Input label="Phone" placeholder="+91 98xxx xxxxx" value={form.phone ?? ""}
                    onChange={e => f("phone", e.target.value)} required/>
                  <Input label="Email" type="email" placeholder="aman@example.com" value={form.email ?? ""}
                    onChange={e => f("email", e.target.value)} required/>
                </div>
              </>
            )}

            {/* ── Step 2: Role & Services ── */}
            {step === 1 && (
              <>
                <LocalSelect label="Role / Designation" value={form.designation ?? ""}
                  onChange={v => f("designation", v)} placeholder="Select role or designation"
                  options={designations.map(d => ({ value: d, label: d }))}/>

                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", display: "block",
                    marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Assigned Services
                    {form.member_type === "technician" && (
                      <span style={{ color: "var(--brand)", fontWeight: 700, marginLeft: 6, textTransform: "none", letterSpacing: 0 }}>
                        · recommended for technicians
                      </span>
                    )}
                  </label>
                  <ChipMultiSelect options={offeringOptions} selected={form.supported_offering_ids ?? []}
                    onToggle={toggleOffering} emptyText="No enabled services yet — add some from Business Profile → Offerings."/>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>Select one or more services</p>
                </div>

                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", display: "block",
                    marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Skills
                  </label>
                  <ChipMultiSelect options={skillChoices.map(s => ({ id: s, label: s }))} selected={selectedSkills}
                    onToggle={toggleSkill} emptyText="No predefined skills for this business category yet."/>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>Select the skills that apply</p>
                </div>

                <ToggleRow label="Can receive job assignments" helper="Allow this member to be assigned to jobs"
                  checked={form.can_receive_assignment ?? true} onChange={v => f("can_receive_assignment", v)}/>
                {!isEdit && (
                  <ToggleRow label="Create login account" helper="Email or SMS will be sent with login details"
                    checked={form.create_login ?? false} onChange={v => f("create_login", v)}/>
                )}
              </>
            )}

            {/* ── Step 3: Work Area & Access ── */}
            {step === 2 && (
              <>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", display: "block",
                    marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Work Area
                  </label>
                  <ChipMultiSelect options={areaOptions} selected={form.service_area_ids ?? []}
                    onToggle={toggleArea} emptyText="No service areas configured yet — add some from Business Profile → Service Areas."/>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
                    Which of your configured service areas this member covers
                  </p>
                </div>

                {form.create_login && !isEdit ? (
                  <div style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--info-border)",
                    background: "var(--info-bg)" }}>
                    <p style={{ fontSize: 12, color: "var(--info-text)", margin: 0 }}>
                      A login account will be created for this member — credentials will be shown once, right after you create them.
                    </p>
                  </div>
                ) : (
                  <div style={{ padding: "10px 12px", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)",
                    border: "1px solid var(--border)" }}>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                      No login account will be created{!isEdit ? " — turn on \"Create login account\" in the previous step if this member needs one" : ""}.
                    </p>
                  </div>
                )}
              </>
            )}

            {/* ── Step 4: Review & Create ── */}
            {step === 3 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <SummaryBlock title="Basic Info" onEdit={() => setStep(0)}>
                  <PreviewRow label="Name" value={form.full_name.trim() || "—"}/>
                  <PreviewRow label="Type" value={typeLabel}/>
                  <PreviewRow label="Phone" value={form.phone || "—"}/>
                  <PreviewRow label="Email" value={form.email || "—"}/>
                </SummaryBlock>

                <SummaryBlock title="Role & Services" onEdit={() => setStep(1)}>
                  <PreviewRow label="Role" value={form.designation || "—"}/>
                  <PreviewRow label="Services" value={selectedServiceLabels.length ? `${selectedServiceLabels.length} selected` : "None"}/>
                  <PreviewRow label="Skills" value={selectedSkills.length ? `${selectedSkills.length} selected` : "None"}/>
                  <PreviewRow label="Job assignments" value={form.can_receive_assignment ? "Enabled" : "Disabled"}/>
                  {!isEdit && <PreviewRow label="Login account" value={form.create_login ? "Will be created" : "Not created"}/>}
                </SummaryBlock>

                <SummaryBlock title="Work Area & Access" onEdit={() => setStep(2)}>
                  <PreviewRow label="Work area" value={selectedAreaLabels.length ? `${selectedAreaLabels.length} area(s)` : "Not set"}/>
                </SummaryBlock>
              </div>
            )}
          </div>

          {/* Right: live preview (visible across all steps) */}
          <div style={{ flex: "0 0 240px", minWidth: 220 }}>
            <div style={{ position: "sticky", top: 0, border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
              background: "var(--surface-sunken)", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
                color: "var(--text-tertiary)", margin: 0 }}>Member Preview</p>

              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, textAlign: "center" }}>
                <DefaultAvatar name={form.full_name || "New Member"} src={photoPreview} size={56}/>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    {form.full_name.trim() || "Unnamed member"}
                  </p>
                  <span style={{ display: "inline-block", marginTop: 4, fontSize: 11, fontWeight: 600, padding: "2px 8px",
                    borderRadius: 999, background: "var(--accent-muted)", color: "var(--brand)" }}>
                    {typeLabel}
                  </span>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
                <PreviewRow label="Phone" value={form.phone || "—"}/>
                <PreviewRow label="Email" value={form.email || "—"}/>
                <PreviewRow label="Role" value={form.designation || "—"}/>
              </div>

              <div>
                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Services</p>
                {selectedServiceLabels.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {selectedServiceLabels.map(l => (
                      <span key={l} style={{ fontSize: 10, padding: "2px 7px", borderRadius: 999,
                        background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>{l}</span>
                    ))}
                  </div>
                ) : <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>None selected</p>}
              </div>

              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                <StatusLine ok={form.can_receive_assignment ?? true} label="Can receive job assignments"/>
                <StatusLine ok={!!form.create_login} label="Login account will be created"/>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
    </div>
  );
}

function StatusLine({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
      {ok ? <CheckCircle2 size={13} style={{ color: "var(--success)", flexShrink: 0 }}/>
          : <XCircle size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0 }}/>}
      <span style={{ color: ok ? "var(--text-primary)" : "var(--text-tertiary)" }}>{label}</span>
    </div>
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

  // Prefer the top-level category_type (always populated, per its own type
  // comment) over category?.category_type / tenant?.category?.category_type,
  // which are frequently unpopulated in real seeded data -- that's why the
  // Member Type / Designation dropdowns were falling back to the generic
  // 3-option list instead of the real Home Services designations.
  const categoryType: string | null =
    runtime.data?.category_type ?? runtime.data?.category?.category_type ?? runtime.data?.tenant?.category?.category_type ?? null;
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
      <div style={{ marginBottom: 20 }}>
        <PageHeader
          title={title}
          description="Manage the people who deliver your services."
          actions={<Button variant="primary" size="sm" leftIcon={<UserPlus size={14}/>}
            onClick={() => { setEditMember(null); setModalOpen(true); }}>Add Member</Button>}
        />
      </div>

      {/* Toasts */}
      {toast    && <div style={{ marginBottom: 12 }}><Alert tone="success">{toast}</Alert></div>}
      {toastErr && <div style={{ marginBottom: 12 }}><Alert tone="danger">{toastErr}</Alert></div>}

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
            <span style={{ fontWeight:700, color:"var(--success)" }}>{activeCount}</span>
            <span style={{ color:"var(--text-secondary)", marginLeft:4 }}>active</span>
          </div>
        </div>
      )}

      {/* Content */}
      {members.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height="4rem"/>)}
        </div>
      ) : members.error ? (
        <Card>
          <div style={{ textAlign:"center", padding:"32px 0" }}>
            <AlertCircle size={28} style={{ color:"var(--danger)", display:"block", margin:"0 auto 10px" }}/>
            <p style={{ fontSize:13, color:"var(--danger)", margin:"0 0 12px" }}>{members.error}</p>
            <Button size="sm" variant="primary" onClick={members.refetch}>Retry</Button>
          </div>
        </Card>
      ) : list.length === 0 ? (
        <Card style={{ textAlign:"center" }}>
          <Users size={32} style={{ color:"var(--text-tertiary)", display:"block", margin:"0 auto 12px" }}/>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:"0 0 12px" }}>No {title.toLowerCase()} yet.</p>
          <Button size="sm" variant="primary" onClick={() => { setEditMember(null); setModalOpen(true); }}>
            Add First Member
          </Button>
        </Card>
      ) : (
        <Card padding="none">
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
                        <span style={{ fontSize:11, fontWeight:600, padding:"2px 8px", borderRadius:999,
                          background:"var(--surface-sunken)", border:"1px solid var(--border)", color:"var(--text-secondary)" }}>
                          {typeLabel}
                        </span>
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
                        <DsStatusBadge status={m.can_receive_assignment ? "active" : "inactive"} size="sm"/>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <DsStatusBadge status={m.status === "active" ? "active" : "inactive"} size="sm"/>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                          <Button size="sm" variant="ghost" onClick={() => {
                            setEditMember(m); setModalOpen(true);
                          }}>
                            <Edit2 size={11}/>
                          </Button>
                          {m.status === "active" ? (
                            <Button size="sm" variant="ghost" loading={deactivateAction.loading}
                              onClick={() => {
                                if (confirm(`Deactivate ${m.full_name}?`)) deactivateAction.execute(m.member_id);
                              }}>
                              Deactivate
                            </Button>
                          ) : (
                            <Button size="sm" variant="ghost" loading={activateAction.loading}
                              onClick={() => activateAction.execute(m.member_id)}>
                              Activate
                            </Button>
                          )}
                          <Button size="sm" variant="ghost"
                            loading={createLoginAction.loading}
                            onClick={() => {
                              if (confirm(`Create login for ${m.full_name}? Credentials will be shown once.`))
                                createLoginAction.execute(m.member_id);
                            }}>
                            <Key size={11}/>
                          </Button>
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
