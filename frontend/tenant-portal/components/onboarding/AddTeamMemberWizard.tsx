"use client";
/**
 * Add/Edit Team Member — ONE complete form, ONE save.
 *
 * Replaces the previous 5-step wizard (Identity -> Role & Access -> Services
 * -> Availability -> Review), which had three real problems beyond just being
 * tedious to get through:
 *
 *  1. It created the member on step 1 and PATCHed it on every later step, so
 *     abandoning the wizard left a half-created, unassignable technician.
 *  2. It stored the new id from `res.member.member_id`, but the backend
 *     returned a raw row whose key is `id` -- so memberId was ALWAYS
 *     undefined and every later step early-returned on `if (!memberId)`.
 *     Role, services, availability and login were silently never saved.
 *     (The backend now also returns `member_id`; see provider_portal/router.py.)
 *  3. Capacity and profile photo were collected but dropped by the create
 *     endpoint's INSERT.
 *
 * Everything is now gathered first and written in a single create/update
 * call, so a member is either fully saved or not created at all. Optional
 * extras that genuinely need their own endpoints (weekly availability, login
 * credentials) run only AFTER the member exists, and their failure is
 * surfaced without falsely reporting the whole save as failed. Readiness is
 * always recomputed server-side; this component never claims a member is
 * "ready" itself.
 */
import React, { useEffect, useState } from "react";
import { X, CheckCircle2, Loader2, Copy } from "lucide-react";
import { Btn } from "../shared/ui";
import { MediaUploader } from "../media/MediaUploader";
import {
  providerTeamMembersApi, providerAvailabilityApi, homeServicesSetupApi, getTenantId,
  ServiceOSError, type ProviderTeamMember, type MediaAsset, type TenantEnabledService,
} from "../../lib/api";

const MEMBER_TYPES = [
  { value: "technician", label: "Technician", hint: "Performs assigned jobs" },
  { value: "staff", label: "Staff", hint: "Non-technician operational staff" },
  { value: "manager", label: "Manager", hint: "Oversees operations" },
];

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function AddTeamMemberWizard({ existing, onClose, onSaved }: {
  existing: ProviderTeamMember | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const tenantId = getTenantId() ?? "";
  const isEdit = !!existing?.member_id;

  // ── Identity ──
  const [fullName, setFullName] = useState(existing?.full_name ?? "");
  const [phone, setPhone] = useState(existing?.phone ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");
  const [designation, setDesignation] = useState(existing?.designation ?? "");
  const [photoAsset, setPhotoAsset] = useState<MediaAsset | null>(null);

  // ── Role & capacity ──
  const [memberType, setMemberType] = useState<string>(existing?.member_type ?? "technician");
  const [canReceive, setCanReceive] = useState<boolean>(existing?.can_receive_assignment ?? true);
  const [maxConcurrent, setMaxConcurrent] = useState<string>(
    existing?.max_concurrent_jobs != null ? String(existing.max_concurrent_jobs) : "4",
  );
  const [skillsText, setSkillsText] = useState((existing?.skills ?? []).join(", "));

  // ── Reporting ──
  const [reportsToName, setReportsToName] = useState("");
  const [reportsToDesignation, setReportsToDesignation] = useState("");

  // ── Services ──
  const [availableServices, setAvailableServices] = useState<TenantEnabledService[]>([]);
  const [selectedOfferingIds, setSelectedOfferingIds] = useState<string[]>(existing?.supported_offering_ids ?? []);

  // ── Optional weekly availability (separate endpoint, create only) ──
  const [addAvailability, setAddAvailability] = useState(false);
  const [dayOfWeek, setDayOfWeek] = useState(1);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("18:00");

  // ── Optional login (separate endpoint, runs after member exists) ──
  const [wantsLogin, setWantsLogin] = useState(false);
  const [activation, setActivation] = useState<
    Awaited<ReturnType<typeof providerTeamMembersApi.createLogin>> | null
  >(null);

  const isTechnician = memberType === "technician";

  // Services load as soon as the form opens for a technician -- the old
  // wizard only fetched them once you reached step 3.
  useEffect(() => {
    if (!isTechnician) return;
    homeServicesSetupApi.listEnabled()
      .then(r => setAvailableServices(r.services.filter(s => s.is_enabled)))
      .catch(() => {});
  }, [isTechnician]);

  function validate(): string | null {
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim() && !phone.trim()) return "Enter an email address or a mobile number.";
    if (maxConcurrent !== "") {
      const cap = Number(maxConcurrent);
      if (!Number.isFinite(cap) || !Number.isInteger(cap) || cap < 1) {
        return "Maximum simultaneous jobs must be a whole number of at least 1.";
      }
    }
    return null;
  }

  async function handleSave() {
    const invalid = validate();
    if (invalid) { setError(invalid); return; }
    setError(""); setWarning(""); setSaving(true);

    const payload = {
      member_type: memberType as ProviderTeamMember["member_type"],
      full_name: fullName.trim(),
      phone: phone.trim() || null,
      email: email.trim() || null,
      designation: designation.trim() || null,
      can_receive_assignment: canReceive,
      max_concurrent_jobs: maxConcurrent === "" ? null : Number(maxConcurrent),
      skills: skillsText.split(",").map(s => s.trim()).filter(Boolean),
      supported_offering_ids: isTechnician ? selectedOfferingIds : [],
      profile_photo_url: photoAsset?.preview_url ?? (isEdit ? undefined : null),
      reports_to_display_name: reportsToName.trim() || null,
      reports_to_designation: reportsToDesignation.trim() || null,
    };

    try {
      let memberId: string;
      if (isEdit) {
        await providerTeamMembersApi.update(existing!.member_id, payload);
        memberId = existing!.member_id;
      } else {
        const res = await providerTeamMembersApi.create(payload);
        memberId = res.member.member_id;
      }

      // Extras run only after the member is safely saved. If one fails the
      // member still exists -- surfaced as a warning, never as "save failed".
      const problems: string[] = [];

      if (!isEdit && addAvailability && isTechnician) {
        try {
          await providerAvailabilityApi.create({
            scope_type: "staff_member", scope_id: memberId,
            day_of_week: dayOfWeek, start_time: startTime, end_time: endTime,
            max_bookings_per_slot: undefined, is_active: true,
          });
        } catch {
          problems.push("weekly availability could not be saved");
        }
      }

      if (wantsLogin) {
        try {
          setActivation(await providerTeamMembersApi.createLogin(memberId));
        } catch {
          problems.push("login access could not be created");
        }
      }

      if (problems.length > 0) {
        setWarning(`Team member saved, but ${problems.join(" and ")}. You can retry from their profile.`);
        setSaving(false);
        return;
      }

      // Credentials are shown once and cannot be retrieved again, so never
      // auto-close over them -- the tenant must copy them first.
      if (wantsLogin) { setSaving(false); return; }

      onSaved();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save this team member.");
      setSaving(false);
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "var(--bg-gradient)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 2px" }}>
            {MEMBER_TYPES.find(t => t.value === memberType)?.label ?? "Team member"} details
          </p>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            {isEdit ? "Edit team member" : "Add team member"}
          </h2>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}><X size={22}/></button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          {error && (
            <div role="alert" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>{error}</div>
          )}
          {warning && (
            <div role="alert" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", color: "var(--warning-text)", fontSize: 13, marginBottom: 16 }}>{warning}</div>
          )}

          {/* ── Identity ── */}
          <SectionTitle>Identity</SectionTitle>
          <Field label="Profile photo">
            <MediaUploader mediaContext="staff_profile_photo" ownerType="tenant" ownerId={tenantId}
              multiple={false} canDelete={false} label="Upload photo" onUploaded={setPhotoAsset}/>
          </Field>
          <Row>
            <Field label="Full name" required><Input value={fullName} onChange={setFullName} placeholder="Enter full name"/></Field>
            <Field label="Designation" hint="Shown to customers, e.g. Senior Technician">
              <Input value={designation} onChange={setDesignation} placeholder="Senior Technician"/>
            </Field>
          </Row>
          <Row>
            <Field label="Mobile number" hint="Email or mobile is required">
              <Input value={phone} onChange={setPhone} placeholder="+91XXXXXXXXXX"/>
            </Field>
            <Field label="Email address" hint="Needed for login access">
              <Input value={email} onChange={setEmail} placeholder="name@business.com"/>
            </Field>
          </Row>

          {/* ── Role & capacity ── */}
          <SectionTitle>Role &amp; assignment</SectionTitle>
          <Field label="Role" required>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 8 }}>
              {MEMBER_TYPES.map(t => (
                <label key={t.value} style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderRadius: 8, border: `1px solid ${memberType === t.value ? "var(--brand)" : "var(--border)"}`, cursor: "pointer" }}>
                  <input type="radio" checked={memberType === t.value} onChange={() => setMemberType(t.value)}/>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{t.label}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{t.hint}</p>
                  </div>
                </label>
              ))}
            </div>
          </Field>
          <Row>
            <Field label="Maximum simultaneous jobs" hint="Used when deciding who can take another job">
              <input type="number" min={1} value={maxConcurrent}
                onChange={e => setMaxConcurrent(e.target.value)} style={selectStyle}/>
            </Field>
            <Field label="Assignment">
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer", height: 40 }}>
                <input type="checkbox" checked={canReceive} onChange={e => setCanReceive(e.target.checked)}/>
                Can be assigned jobs
              </label>
            </Field>
          </Row>
          <Field label="Skills" hint="Comma separated, e.g. AC Repair, Installation">
            <Input value={skillsText} onChange={setSkillsText} placeholder="AC Repair, Installation"/>
          </Field>
          <Row>
            <Field label="Reports to" hint="Shown on the member's Help &amp; Support screen">
              <Input value={reportsToName} onChange={setReportsToName} placeholder="Manager name"/>
            </Field>
            <Field label="Reports-to designation">
              <Input value={reportsToDesignation} onChange={setReportsToDesignation} placeholder="Operations Manager"/>
            </Field>
          </Row>

          {/* ── Services (technicians only) ── */}
          {isTechnician && (
            <>
              <SectionTitle>Services this technician can perform</SectionTitle>
              <Field label="Services &amp; job types" hint="A technician can only be assigned jobs for the services selected here.">
                {availableServices.length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                    No services enabled yet — configure Services &amp; Pricing first.
                  </p>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8 }}>
                    {availableServices.map(s => (
                      <label key={s.tenant_service_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 8, border: "1px solid var(--border)", cursor: "pointer" }}>
                        <input type="checkbox" checked={selectedOfferingIds.includes(s.tenant_service_id)}
                          onChange={e => setSelectedOfferingIds(prev => e.target.checked
                            ? [...prev, s.tenant_service_id]
                            : prev.filter(id => id !== s.tenant_service_id))}/>
                        <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{s.tenant_display_name || s.job_type}</span>
                      </label>
                    ))}
                  </div>
                )}
              </Field>
            </>
          )}

          {/* ── Optional weekly availability (create only) ── */}
          {isTechnician && !isEdit && (
            <>
              <SectionTitle>Weekly availability<Optional/></SectionTitle>
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer", marginBottom: 12 }}>
                <input type="checkbox" checked={addAvailability} onChange={e => setAddAvailability(e.target.checked)}/>
                Set a working window now (you can add more later)
              </label>
              {addAvailability && (
                <Row3>
                  <Field label="Day">
                    <select value={dayOfWeek} onChange={e => setDayOfWeek(Number(e.target.value))} style={selectStyle}>
                      {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                    </select>
                  </Field>
                  <Field label="Start time"><input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} style={selectStyle}/></Field>
                  <Field label="End time"><input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} style={selectStyle}/></Field>
                </Row3>
              )}
            </>
          )}

          {/* ── Optional login ── */}
          <SectionTitle>Login access<Optional/></SectionTitle>
          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
            <input type="checkbox" checked={wantsLogin} onChange={e => setWantsLogin(e.target.checked)}/>
            Create login access so this member can use the app
          </label>
          {activation && (
            <div style={{ padding: 14, borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", marginTop: 12 }}>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>
                {activation.already_had_login
                  ? "Login access already exists for this team member."
                  : activation.activation_sent
                    ? "Invitation sent. The team member will choose their own password using the one-time activation code."
                    : activation.activation_token
                      ? "Invitation created. Email delivery is not configured here; share this development activation code securely."
                      : "Invitation created, but delivery could not be confirmed. Retry from the member profile."}
              </p>
              {activation.activation_token && (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <code style={{ fontSize: 11, background: "var(--surface)", padding: "6px 8px", borderRadius: 6, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {activation.activation_token}
                  </code>
                  <button
                    aria-label="Copy activation code"
                    onClick={() => navigator.clipboard?.writeText(activation.activation_token!)}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}
                  ><Copy size={14}/></button>
                </div>
              )}
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 20, padding: "10px 12px", borderRadius: 8, background: "var(--success-bg)", border: "1px solid var(--success-border)" }}>
            <CheckCircle2 size={16} style={{ color: "var(--success)" }}/>
            <span style={{ fontSize: 12, color: "var(--success-text)" }}>Readiness is recalculated automatically after saving.</span>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", padding: "16px 24px", borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <div style={{ display: "flex", gap: 10 }}>
          {activation && <Btn variant="secondary" onClick={onSaved}>Done</Btn>}
          <Btn variant="primary" disabled={saving} onClick={handleSave}>
            {saving
              ? <Loader2 size={15} style={{ animation: "spin 0.8s linear infinite" }}/>
              : <>{isEdit ? "Save changes" : "Add team member"} <CheckCircle2 size={15}/></>}
          </Btn>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{
      fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
      color: "var(--text-tertiary)", margin: "24px 0 12px", paddingBottom: 6,
      borderBottom: "1px solid var(--border)",
    }}>{children}</h3>
  );
}
function Optional() {
  return <span style={{ fontWeight: 500, textTransform: "none", letterSpacing: 0, color: "var(--text-tertiary)" }}> — optional</span>;
}
function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>{children}</div>;
}
function Row3({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>{children}</div>;
}
function Field({ label, required, hint, children }: { label: string; required?: boolean; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
        {label}{required && <span style={{ color: "var(--danger)" }}> *</span>}
      </label>
      {children}
      {hint && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{hint}</p>}
    </div>
  );
}
function Input({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={selectStyle}/>;
}
const selectStyle: React.CSSProperties = {
  width: "100%", height: 40, padding: "0 12px", fontSize: 13, borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)",
  boxSizing: "border-box", fontFamily: "inherit",
};
