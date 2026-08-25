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
import React, { useEffect, useRef, useState } from "react";
import { X, CheckCircle2, Loader2, Copy, Search, ShieldCheck } from "lucide-react";
import { Btn } from "../shared/ui";
import { ProfilePhotoUploader } from "../shared/ProfilePhotoUploader";
import {
  providerTeamMembersApi, providerTeamSkillsApi, homeServicesSetupApi, getTenantId,
  ServiceOSError, type ProviderTeamMember, type MediaAsset, type TenantEnabledService,
  type CategoryTeamSkill,
} from "../../lib/api";

const MEMBER_TYPES = [
  { value: "technician", label: "Technician", hint: "Performs assigned jobs" },
  { value: "staff", label: "Staff", hint: "Non-technician operational staff" },
  { value: "manager", label: "Manager", hint: "Oversees operations" },
];

const DESIGNATIONS_BY_MEMBER_TYPE: Record<string, string[]> = {
  technician: [
    "Technician", "Junior Technician", "Senior Technician", "Lead Technician",
    "AC Technician", "Installation Specialist", "Maintenance Specialist", "Field Supervisor",
  ],
  staff: [
    "Operations Coordinator", "Dispatcher", "Customer Support Executive", "Back Office Executive",
  ],
  manager: [
    "Team Manager", "Operations Manager", "Service Manager", "Branch Manager",
  ],
};

const ALL_DESIGNATIONS = Array.from(
  new Set(Object.values(DESIGNATIONS_BY_MEMBER_TYPE).flat()),
).sort((a, b) => a.localeCompare(b));

function humanizeJobType(value: string) {
  return value.split("_").filter(Boolean).map(part => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function AddTeamMemberWizard({ existing, onClose, onSaved }: {
  existing: ProviderTeamMember | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [completed, setCompleted] = useState(false);
  const tenantId = getTenantId() ?? "";
  const isEdit = !!existing?.member_id;

  // ── Identity ──
  const [fullName, setFullName] = useState(existing?.full_name ?? "");
  const [phone, setPhone] = useState(existing?.phone ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");
  const [designation, setDesignation] = useState(existing?.designation ?? "");
  const [photoAsset, setPhotoAsset] = useState<MediaAsset | null>(null);
  // Distinguishes "left the existing photo alone" from "explicitly cleared it",
  // so an edit that removes the photo actually persists the removal.
  const [photoCleared, setPhotoCleared] = useState(false);

  // ── Role & capacity ──
  const [memberType, setMemberType] = useState<string>(existing?.member_type ?? "technician");
  const [canReceive, setCanReceive] = useState<boolean>(existing?.can_receive_assignment ?? true);
  const [availableSkills, setAvailableSkills] = useState<CategoryTeamSkill[]>([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>(existing?.skill_ids ?? []);
  const [skillSearch, setSkillSearch] = useState("");
  const [skillsLoadFailed, setSkillsLoadFailed] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // ── Reporting ──
  const [reportsToName, setReportsToName] = useState("");
  const [reportsToDesignation, setReportsToDesignation] = useState("");

  // ── Services ──
  const [availableServices, setAvailableServices] = useState<TenantEnabledService[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [servicesLoadFailed, setServicesLoadFailed] = useState(false);
  const [selectedOfferingIds, setSelectedOfferingIds] = useState<string[]>(existing?.supported_offering_ids ?? []);

  // New technicians inherit the provider's active business schedule by
  // default. Readiness and booking capacity both use these staff-level rules.

  // ── Optional login (separate endpoint, runs after member exists) ──
  const [wantsLogin, setWantsLogin] = useState(false);
  const [activation, setActivation] = useState<
    Awaited<ReturnType<typeof providerTeamMembersApi.createLogin>> | null
  >(null);

  const isTechnician = memberType === "technician";
  const hasDeliverableEmail = email.trim().length > 0;
  const designationOptions = React.useMemo(() => {
    const values = DESIGNATIONS_BY_MEMBER_TYPE[memberType] ?? [];
    return designation && !values.includes(designation) ? [designation, ...values] : values;
  }, [memberType, designation]);
  const groupedServices = React.useMemo(() => {
    const byMasterService = new Map<string, {
      id: string;
      name: string;
      serviceGroupName: string | null;
      offerings: TenantEnabledService[];
    }>();
    for (const offering of availableServices) {
      const existingGroup = byMasterService.get(offering.master_service_id);
      if (existingGroup) {
        if (!existingGroup.offerings.some(item => item.tenant_service_id === offering.tenant_service_id)) {
          existingGroup.offerings.push(offering);
        }
        continue;
      }
      byMasterService.set(offering.master_service_id, {
        id: offering.master_service_id,
        name: offering.tenant_display_name || offering.service_name || "Unnamed service",
        serviceGroupName: offering.service_group_name ?? null,
        offerings: [offering],
      });
    }
    return Array.from(byMasterService.values());
  }, [availableServices]);

  useEffect(() => {
    if (!hasDeliverableEmail) setWantsLogin(false);
  }, [hasDeliverableEmail]);

  // Services load as soon as the form opens for a technician -- the old
  // wizard only fetched them once you reached step 3.
  useEffect(() => {
    if (!isTechnician) {
      setServicesLoading(false);
      setServicesLoadFailed(false);
      return;
    }
    let cancelled = false;
    setServicesLoading(true);
    setServicesLoadFailed(false);
    Promise.all([homeServicesSetupApi.listEnabled(), providerTeamSkillsApi.list()])
      .then(([services, skills]) => {
        if (!cancelled) {
          setAvailableServices(services.services.filter(s => s.is_enabled));
          setAvailableSkills(skills.skills);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setServicesLoadFailed(true);
          setSkillsLoadFailed(true);
        }
      })
      .finally(() => {
        if (!cancelled) setServicesLoading(false);
      });
    return () => { cancelled = true; };
  }, [isTechnician]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose, saving]);

  function validate(): string | null {
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim() && !phone.trim()) return "Enter an email address or a mobile number.";
    if (!designation.trim()) return "Select a designation.";
    if (isTechnician && servicesLoading) return "Wait for the enabled services to finish loading.";
    if (isTechnician && servicesLoadFailed) return "Enabled services could not be loaded. Close this dialog and try again.";
    if (isTechnician && availableServices.length === 0) return "Configure at least one enabled service before adding a technician.";
    if (isTechnician && availableServices.length > 0 && selectedOfferingIds.length === 0) {
      return "Select at least one service this technician can perform.";
    }
    if (isTechnician && skillsLoadFailed) return "The approved skill catalog could not be loaded. Close this dialog and try again.";
    if (isTechnician && availableSkills.length === 0) return "No active technician skills are configured for this category. Ask an administrator to configure the skill catalog.";
    if (isTechnician && selectedSkillIds.length === 0) return "Select at least one approved skill for this technician.";
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
      skill_ids: isTechnician ? selectedSkillIds : [],
      supported_offering_ids: isTechnician ? selectedOfferingIds : [],
      profile_photo_url: photoAsset?.preview_url ?? (photoCleared || !isEdit ? null : undefined),
      ...(!isEdit ? { inherit_business_hours: isTechnician } : {}),
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

      if (wantsLogin) {
        try {
          setActivation(await providerTeamMembersApi.createLogin(memberId));
        } catch {
          problems.push("login access could not be created");
        }
      }

      if (problems.length > 0) {
        setWarning(`Team member saved, but ${problems.join(" and ")}. You can retry from their profile.`);
        setCompleted(true);
        setSaving(false);
        return;
      }

      // Credentials are shown once and cannot be retrieved again, so never
      // auto-close over them -- the tenant must copy them first.
      if (wantsLogin) { setCompleted(true); setSaving(false); return; }

      onSaved();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save this team member.");
      setSaving(false);
    }
  }

  return (
    <div
      role="presentation"
      onMouseDown={event => { if (event.target === event.currentTarget && !saving) onClose(); }}
      style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(7, 12, 20, 0.68)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
    >
      <div role="dialog" aria-modal="true" aria-labelledby="team-member-dialog-title" style={{ width: "min(900px, 100%)", maxHeight: "calc(100vh - 40px)", borderRadius: 16, border: "1px solid var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-lg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <div>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 2px" }}>
            {MEMBER_TYPES.find(t => t.value === memberType)?.label ?? "Team member"} details
          </p>
          <h2 id="team-member-dialog-title" style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            {isEdit ? "Edit team member" : "Add team member"}
          </h2>
        </div>
        <button ref={closeButtonRef} onClick={onClose} aria-label="Close team member dialog" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}><X size={22}/></button>
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
          <Field label="Profile photo" hint="JPG, PNG or WebP up to 5 MB. Crop the face to the centre of the circle.">
            <ProfilePhotoUploader
              ownerType="staff_managed"
              ownerId={tenantId}
              currentPreviewUrl={photoAsset?.preview_url ?? existing?.profile_photo_url ?? null}
              currentMediaId={photoAsset?.id ?? null}
              displayName={fullName || existing?.full_name}
              size="lg"
              onUploaded={asset => { setPhotoAsset(asset); setPhotoCleared(false); }}
              onRemoved={() => { setPhotoAsset(null); setPhotoCleared(true); }}
            />
          </Field>
          <Row>
            <Field label="Full name" required><Input value={fullName} onChange={setFullName} placeholder="Enter full name"/></Field>
            <Field label="Designation" required hint="Shown to customers and used in team directories.">
              <select value={designation} onChange={event => setDesignation(event.target.value)}
                style={{ width: "100%", height: 40, padding: "0 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
                <option value="">Select designation</option>
                {designationOptions.map(value => <option key={value} value={value}>{value}</option>)}
              </select>
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
                  <input type="radio" checked={memberType === t.value} onChange={() => {
                    setMemberType(t.value);
                    if (!(DESIGNATIONS_BY_MEMBER_TYPE[t.value] ?? []).includes(designation)) setDesignation("");
                  }}/>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{t.label}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{t.hint}</p>
                  </div>
                </label>
              ))}
            </div>
          </Field>
          <Row>
            <Field label="Assignment" hint="Slot capacity is calculated automatically from ready technicians; it cannot exceed the available team.">
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer", height: 40 }}>
                <input type="checkbox" checked={canReceive} onChange={e => setCanReceive(e.target.checked)}/>
                Can be assigned jobs
              </label>
            </Field>
          </Row>
          {isTechnician && (
            <Field label="Approved skills" required hint="Skills are controlled by the platform administrator for this business category.">
              {servicesLoading ? (
                <p role="status" style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Loading approved skills...</p>
              ) : skillsLoadFailed ? (
                <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>The approved skill catalog could not be loaded.</p>
              ) : availableSkills.length === 0 ? (
                <div style={{ padding: 12, borderRadius: 8, border: "1px solid var(--warning-border)", background: "var(--warning-bg)", color: "var(--warning-text)", fontSize: 12 }}>
                  No active skills are configured for this category. An administrator must add skills before technicians can be created.
                </div>
              ) : (
                <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
                  <div style={{ position: "relative", borderBottom: "1px solid var(--border)" }}>
                    <Search size={14} style={{ position: "absolute", left: 12, top: 12, color: "var(--text-tertiary)" }}/>
                    <input value={skillSearch} onChange={e => setSkillSearch(e.target.value)} placeholder="Search approved skills..."
                      style={{ width: "100%", height: 38, padding: "0 12px 0 36px", border: 0, outline: 0, background: "var(--surface-sunken)", color: "var(--text-primary)", boxSizing: "border-box" }}/>
                  </div>
                  <div style={{ maxHeight: 230, overflowY: "auto", padding: 8, display: "grid", gap: 6 }}>
                    {availableSkills.filter(skill => `${skill.name} ${skill.description ?? ""} ${skill.service_group_name ?? ""}`.toLowerCase().includes(skillSearch.trim().toLowerCase())).map(skill => {
                      const checked = selectedSkillIds.includes(skill.id);
                      return (
                        <label key={skill.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 11px", borderRadius: 8, cursor: "pointer", border: `1px solid ${checked ? "var(--brand)" : "var(--border)"}`, background: checked ? "color-mix(in srgb, var(--brand) 7%, var(--surface))" : "var(--surface)" }}>
                          <input type="checkbox" checked={checked} onChange={e => setSelectedSkillIds(prev => e.target.checked ? [...prev, skill.id] : prev.filter(id => id !== skill.id))} style={{ marginTop: 2 }}/>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                              <span style={{ fontSize: 13, fontWeight: 650, color: "var(--text-primary)" }}>{skill.name}</span>
                              {skill.service_group_name && <span style={{ fontSize: 10, color: "var(--text-tertiary)", padding: "2px 6px", borderRadius: 999, background: "var(--surface-sunken)" }}>{skill.service_group_name}</span>}
                              {skill.requires_verification && <span title="Verification required" style={{ display: "inline-flex", color: "var(--warning)" }}><ShieldCheck size={13}/></span>}
                            </div>
                            {skill.description && <p style={{ margin: "3px 0 0", fontSize: 11, color: "var(--text-tertiary)", lineHeight: 1.4 }}>{skill.description}</p>}
                          </div>
                        </label>
                      );
                    })}
                  </div>
                  <div style={{ padding: "8px 11px", borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {selectedSkillIds.length} skill{selectedSkillIds.length === 1 ? "" : "s"} selected. Shield-marked skills require verification.
                  </div>
                </div>
              )}
            </Field>
          )}
          <Row>
            <Field label="Reports to" hint="Shown on the member's Help &amp; Support screen">
              <Input value={reportsToName} onChange={setReportsToName} placeholder="Manager name"/>
            </Field>
            <Field label="Reports-to designation">
              <select value={reportsToDesignation} onChange={event => setReportsToDesignation(event.target.value)}
                aria-label="Reports-to designation"
                style={{ width: "100%", height: 40, padding: "0 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}>
                <option value="">Select reporting designation (optional)</option>
                {ALL_DESIGNATIONS.map(value => <option key={value} value={value}>{value}</option>)}
              </select>
            </Field>
          </Row>

          {/* ── Services (technicians only) ── */}
          {isTechnician && (
            <>
              <SectionTitle>Services this technician can perform</SectionTitle>
              <Field label="Services &amp; job types" hint="A technician can only be assigned jobs for the services selected here.">
                {servicesLoading ? (
                  <p role="status" style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                    Loading enabled services…
                  </p>
                ) : servicesLoadFailed ? (
                  <p role="alert" style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>
                    Enabled services could not be loaded. Close this dialog and try again.
                  </p>
                ) : availableServices.length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                    No services enabled yet — configure Services &amp; Pricing first.
                  </p>
                ) : (
                  <div style={{ display: "grid", gap: 10 }}>
                    {groupedServices.map(service => {
                      const offeringIds = service.offerings.map(item => item.tenant_service_id);
                      const selectedCount = offeringIds.filter(id => selectedOfferingIds.includes(id)).length;
                      const allSelected = selectedCount === offeringIds.length;
                      return (
                        <div key={service.id} style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden", background: "var(--surface)" }}>
                          <label style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", cursor: "pointer", background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                            <input type="checkbox" checked={allSelected}
                              ref={input => { if (input) input.indeterminate = selectedCount > 0 && !allSelected; }}
                              onChange={event => setSelectedOfferingIds(previous => event.target.checked
                                ? Array.from(new Set([...previous, ...offeringIds]))
                                : previous.filter(id => !offeringIds.includes(id)))}/>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{service.name}</p>
                              {service.serviceGroupName && <p style={{ margin: "2px 0 0", fontSize: 10, color: "var(--text-tertiary)" }}>{service.serviceGroupName}</p>}
                            </div>
                            <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{selectedCount}/{offeringIds.length} job types</span>
                          </label>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 6, padding: 8 }}>
                            {service.offerings.map(offering => {
                              const checked = selectedOfferingIds.includes(offering.tenant_service_id);
                              const jobTypeLabel = offering.job_type_label || humanizeJobType(offering.job_type);
                              return (
                                <label key={offering.tenant_service_id} style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 9px", borderRadius: 7, border: `1px solid ${checked ? "var(--brand)" : "var(--border)"}`, cursor: "pointer" }}>
                                  <input type="checkbox" checked={checked}
                                    onChange={event => setSelectedOfferingIds(previous => event.target.checked
                                      ? Array.from(new Set([...previous, offering.tenant_service_id]))
                                      : previous.filter(id => id !== offering.tenant_service_id))}/>
                                  <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{jobTypeLabel}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Field>
            </>
          )}

          {/* ── Weekly availability (create only) ── */}
          {isTechnician && !isEdit && (
            <>
              <SectionTitle>Weekly availability</SectionTitle>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                This technician will use the business hours configured in Coverage &amp; availability. Each inherited open day creates one technician place in each matching slot; individual availability can be customized after setup.
              </p>
            </>
          )}

          {/* ── Optional login ── */}
          <SectionTitle>Login access<Optional/></SectionTitle>
          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: hasDeliverableEmail ? "var(--text-primary)" : "var(--text-tertiary)", cursor: hasDeliverableEmail ? "pointer" : "not-allowed" }}>
            <input type="checkbox" checked={wantsLogin} disabled={!hasDeliverableEmail}
              onChange={e => setWantsLogin(e.target.checked)}/>
            Create login access so this member can use the app
          </label>
          {!hasDeliverableEmail && (
            <p style={{ margin: "6px 0 0 24px", fontSize: 11, color: "var(--text-tertiary)" }}>
              You can add this technician now. Add an email later, then use “Send app invitation” from the actions menu.
            </p>
          )}
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
          {completed ? (
            <Btn variant="primary" onClick={onSaved}>Done</Btn>
          ) : (
            <Btn variant="primary" disabled={saving} onClick={handleSave}>
              {saving
                ? <Loader2 size={15} style={{ animation: "spin 0.8s linear infinite" }}/>
                : <>{isEdit ? "Save changes" : "Add team member"} <CheckCircle2 size={15}/></>}
            </Btn>
          )}
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
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
