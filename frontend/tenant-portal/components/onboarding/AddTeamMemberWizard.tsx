"use client";
/**
 * Add/Edit Team Member — dedicated multistep wizard (full-screen overlay,
 * not a long single modal): Identity -> Role & Access -> Services & Skills
 * -> Availability -> Review. Readiness is always recomputed server-side
 * after save — this component never claims a member is "ready" itself.
 */
import React, { useEffect, useState } from "react";
import { X, ArrowRight, ArrowLeft, CheckCircle2, Loader2, Copy } from "lucide-react";
import { Btn, Badge } from "../shared/ui";
import { MediaUploader } from "../media/MediaUploader";
import {
  providerTeamMembersApi, providerAvailabilityApi, homeServicesSetupApi, getTenantId,
  ServiceOSError, type ProviderTeamMember, type MediaAsset, type TenantEnabledService,
} from "../../lib/api";

type Step = "identity" | "access" | "services" | "availability" | "review";
const STEPS: { key: Step; label: string }[] = [
  { key: "identity", label: "Identity" },
  { key: "access", label: "Role & Access" },
  { key: "services", label: "Services & Skills" },
  { key: "availability", label: "Availability" },
  { key: "review", label: "Review & Add" },
];

const MEMBER_TYPES = [
  { value: "technician", label: "Technician", hint: "Performs assigned jobs" },
  { value: "staff", label: "Staff", hint: "Non-technician operational staff" },
  { value: "manager", label: "Manager", hint: "Oversees operations" },
];

export function AddTeamMemberWizard({ existing, onClose, onSaved }: {
  existing: ProviderTeamMember | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [step, setStep] = useState<Step>("identity");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const tenantId = getTenantId() ?? "";

  const [memberId, setMemberId] = useState<string | null>(existing?.member_id ?? null);
  const [fullName, setFullName] = useState(existing?.full_name ?? "");
  const [phone, setPhone] = useState(existing?.phone ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");
  const [photoAsset, setPhotoAsset] = useState<MediaAsset | null>(null);

  const [memberType, setMemberType] = useState<string>(existing?.member_type ?? "technician");
  const [wantsLogin, setWantsLogin] = useState(false);
  // Real bug fixed here: this state used to be typed `{ activation_token,
  // message }`, but `createLogin` returns `{ member_id, credentials }`. The
  // panel below therefore rendered an undefined message and an activation
  // token that never existed, while silently DROPPING the username and
  // password -- the one thing the tenant needs to hand the new member.
  const [activation, setActivation] = useState<
    { member_id: string; credentials?: { username: string; password: string } | null } | null
  >(null);

  const [availableServices, setAvailableServices] = useState<TenantEnabledService[]>([]);
  const [selectedOfferingIds, setSelectedOfferingIds] = useState<string[]>(existing?.supported_offering_ids ?? []);

  const [dayOfWeek, setDayOfWeek] = useState(1);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("18:00");
  const [maxJobsPerDay, setMaxJobsPerDay] = useState(5);
  const [availabilitySaved, setAvailabilitySaved] = useState(false);

  const isTechnician = memberType === "technician";
  const stepIndex = STEPS.findIndex(s => s.key === step);

  useEffect(() => {
    if (step === "services" && isTechnician) {
      homeServicesSetupApi.listEnabled().then(r => setAvailableServices(r.services.filter(s => s.is_enabled))).catch(() => {});
    }
  }, [step, isTechnician]);

  function next() {
    const order: Step[] = isTechnician
      ? ["identity", "access", "services", "availability", "review"]
      : ["identity", "access", "review"];
    const i = order.indexOf(step);
    if (i < order.length - 1) setStep(order[i + 1]);
  }
  function back() {
    const order: Step[] = isTechnician
      ? ["identity", "access", "services", "availability", "review"]
      : ["identity", "access", "review"];
    const i = order.indexOf(step);
    if (i > 0) setStep(order[i - 1]);
  }

  async function saveIdentity() {
    if (!fullName.trim()) return setError("Full name is required.");
    setError(""); setSaving(true);
    try {
      if (memberId) {
        await providerTeamMembersApi.update(memberId, {
          full_name: fullName.trim(), phone: phone || null, email: email || null,
          profile_photo_url: photoAsset?.preview_url ?? undefined,
        });
      } else {
        const res = await providerTeamMembersApi.create({
          member_type: memberType as ProviderTeamMember["member_type"],
          full_name: fullName.trim(), phone: phone || null, email: email || null,
          profile_photo_url: photoAsset?.preview_url ?? null,
        });
        setMemberId(res.member.member_id);
      }
      next();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save identity details.");
    } finally { setSaving(false); }
  }

  async function saveAccess() {
    if (!memberId) return;
    setError(""); setSaving(true);
    try {
      await providerTeamMembersApi.update(memberId, { member_type: memberType as ProviderTeamMember["member_type"] });
      if (wantsLogin && (email || phone)) {
        const res = await providerTeamMembersApi.createLogin(memberId);
        setActivation(res);
      }
      next();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save role & access.");
    } finally { setSaving(false); }
  }

  async function saveServices() {
    if (!memberId) return;
    if (isTechnician && selectedOfferingIds.length === 0) {
      setError("Select at least one service this technician can perform.");
      return;
    }
    setError(""); setSaving(true);
    try {
      await providerTeamMembersApi.update(memberId, { supported_offering_ids: selectedOfferingIds });
      next();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save service assignments.");
    } finally { setSaving(false); }
  }

  async function saveAvailability() {
    if (!memberId) return;
    setError(""); setSaving(true);
    try {
      await providerAvailabilityApi.create({
        scope_type: "staff_member", scope_id: memberId,
        day_of_week: dayOfWeek, start_time: startTime, end_time: endTime,
        max_bookings_per_slot: undefined, is_active: true,
      });
      setAvailabilitySaved(true);
      next();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save availability.");
    } finally { setSaving(false); }
  }

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "var(--bg-gradient)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Step {stepIndex + 1} of {isTechnician ? 5 : 3}</p>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{existing ? "Edit team member" : "Add team member"} — {STEPS.find(s => s.key === step)?.label}</h2>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}><X size={22}/></button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "28px 24px" }}>
        <div style={{ maxWidth: 560, margin: "0 auto" }}>
          {error && (
            <div role="alert" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>{error}</div>
          )}

          {step === "identity" && (
            <div>
              <Field label="Profile photo">
                <MediaUploader mediaContext="staff_profile_photo" ownerType="tenant" ownerId={tenantId}
                  multiple={false} canDelete={false} label="Upload photo" onUploaded={setPhotoAsset}/>
              </Field>
              <Field label="Full name" required><Input value={fullName} onChange={setFullName} placeholder="Enter full name"/></Field>
              <Field label="Mobile number"><Input value={phone} onChange={setPhone} placeholder="+91XXXXXXXXXX"/></Field>
              <Field label="Email address" hint="Required for login access"><Input value={email} onChange={setEmail} placeholder="name@business.com"/></Field>
            </div>
          )}

          {step === "access" && (
            <div>
              <Field label="Role" required>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
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
              <Field label="Account access">
                <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
                  <input type="checkbox" checked={wantsLogin} onChange={e => setWantsLogin(e.target.checked)}/>
                  Create login access now (requires email or mobile)
                </label>
              </Field>
              {activation && (
                <div style={{ padding: 14, borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", marginTop: 12 }}>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 8px" }}>
                    {activation.credentials
                      ? "Login created. Share these credentials with your team member — the password is shown only once."
                      : "Login created for this team member."}
                  </p>
                  {activation.credentials && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <code style={{ fontSize: 11, background: "var(--surface)", padding: "6px 8px", borderRadius: 6, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                        {activation.credentials.username} / {activation.credentials.password}
                      </code>
                      <button
                        onClick={() => navigator.clipboard?.writeText(
                          `${activation.credentials!.username} / ${activation.credentials!.password}`,
                        )}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}
                      ><Copy size={14}/></button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {step === "services" && (
            <div>
              <Field label="Services & Job Types" required hint="This technician can only be assigned jobs for the exact services selected here.">
                {availableServices.length === 0 && <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No services enabled yet — configure Services & Pricing first.</p>}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {availableServices.map(s => (
                    <label key={s.tenant_service_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 8, border: "1px solid var(--border)", cursor: "pointer" }}>
                      <input type="checkbox" checked={selectedOfferingIds.includes(s.tenant_service_id)}
                        onChange={e => setSelectedOfferingIds(prev => e.target.checked ? [...prev, s.tenant_service_id] : prev.filter(id => id !== s.tenant_service_id))}/>
                      <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{s.tenant_display_name || s.job_type}</span>
                    </label>
                  ))}
                </div>
              </Field>
            </div>
          )}

          {step === "availability" && (
            <div>
              <Field label="Day of week">
                <select value={dayOfWeek} onChange={e => setDayOfWeek(Number(e.target.value))} style={selectStyle}>
                  {["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"].map((d, i) => <option key={d} value={i}>{d}</option>)}
                </select>
              </Field>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="Start time"><input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} style={selectStyle}/></Field>
                <Field label="End time"><input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} style={selectStyle}/></Field>
              </div>
              <Field label="Maximum simultaneous active jobs">
                <input type="number" min={1} value={maxJobsPerDay} onChange={e => setMaxJobsPerDay(Number(e.target.value))} style={selectStyle}/>
              </Field>
            </div>
          )}

          {step === "review" && (
            <div>
              <ReviewRow label="Name" value={fullName}/>
              <ReviewRow label="Contact" value={email || phone || "—"}/>
              <ReviewRow label="Role" value={MEMBER_TYPES.find(t => t.value === memberType)?.label ?? memberType}/>
              {isTechnician && <ReviewRow label="Services" value={`${selectedOfferingIds.length} assigned`}/>}
              {isTechnician && <ReviewRow label="Availability" value={availabilitySaved ? "Configured" : "Not configured"}/>}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 16, padding: "10px 12px", borderRadius: 8, background: "var(--success-bg)", border: "1px solid var(--success-border)" }}>
                <CheckCircle2 size={16} style={{ color: "var(--success)" }}/>
                <span style={{ fontSize: 12, color: "var(--success-text)" }}>Readiness will be recalculated after saving.</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", padding: "16px 24px", borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
        <Btn variant="secondary" onClick={step === "identity" ? onClose : back}>
          <ArrowLeft size={15}/> {step === "identity" ? "Cancel" : "Back"}
        </Btn>
        {step === "review" ? (
          <Btn variant="primary" onClick={onSaved} disabled={saving}>
            {existing ? "Save changes" : "Add team member"} <CheckCircle2 size={15}/>
          </Btn>
        ) : (
          <Btn variant="primary" disabled={saving} onClick={
            step === "identity" ? saveIdentity :
            step === "access" ? saveAccess :
            step === "services" ? saveServices :
            saveAvailability
          }>
            {saving ? <Loader2 size={15} style={{ animation: "spin 0.8s linear infinite" }}/> : <>Continue <ArrowRight size={15}/></>}
          </Btn>
        )}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
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
function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{value}</span>
    </div>
  );
}
const selectStyle: React.CSSProperties = {
  width: "100%", height: 40, padding: "0 12px", fontSize: 13, borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)",
  boxSizing: "border-box", fontFamily: "inherit",
};
