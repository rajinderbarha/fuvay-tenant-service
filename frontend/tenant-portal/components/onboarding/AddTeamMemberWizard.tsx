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
import { X, CheckCircle2, ChevronLeft, ChevronRight, Loader2, Search, ShieldCheck } from "lucide-react";
import { Btn, Input } from "../shared/ui";
import { ProfilePhotoUploader } from "../shared/ProfilePhotoUploader";
import { TeamLoginCredentials } from "./TeamLoginCredentials";
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

const EDIT_SECTIONS = ["Identity", "Role & assignment", "Approved skills", "Services", "Login access"] as const;

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

export function AddTeamMemberWizard({ existing, onClose, onSaved, technicianSeatAvailable = true, initialSection = 0 }: {
  existing: ProviderTeamMember | null;
  onClose: () => void;
  onSaved: () => void;
  technicianSeatAvailable?: boolean;
  initialSection?: number;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [completed, setCompleted] = useState(false);
  const [activeSection, setActiveSection] = useState(initialSection);
  const [memberStatus, setMemberStatus] = useState(existing?.status ?? "active");
  const [skillsReload, setSkillsReload] = useState(0);
  const tenantId = getTenantId() ?? "";
  const isEdit = !!existing?.member_id;

  // ── Identity ──
  const [fullName, setFullName] = useState(existing?.full_name ?? "");
  const [phone, setPhone] = useState(existing?.phone ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");
  const [photoAsset, setPhotoAsset] = useState<MediaAsset | null>(null);
  // Distinguishes "left the existing photo alone" from "explicitly cleared it",
  // so an edit that removes the photo actually persists the removal.
  const [photoCleared, setPhotoCleared] = useState(false);

  // ── Role & capacity ──
  const [memberType, setMemberType] = useState<string>(existing?.member_type ?? (technicianSeatAvailable ? "technician" : "staff"));
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

  // Technicians resolve the provider's current business hours dynamically,
  // so future schedule edits apply immediately without stale copied rows.

  // ── Optional login (separate endpoint, runs after member exists) ──
  const [wantsLogin, setWantsLogin] = useState(false);
  const [activation, setActivation] = useState<
    Awaited<ReturnType<typeof providerTeamMembersApi.generatePassword>> | null
  >(null);

  const isTechnician = memberType === "technician";
  const hasDeliverableEmail = email.trim().length > 0;
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
    setSkillsLoadFailed(false);
    Promise.allSettled([homeServicesSetupApi.listEnabled(), providerTeamSkillsApi.list()])
      .then(([services, skills]) => {
        if (!cancelled) {
          if (services.status === "fulfilled") setAvailableServices(services.value.services.filter(s => s.is_enabled));
          else setServicesLoadFailed(true);
          if (skills.status === "fulfilled") setAvailableSkills(skills.value.skills);
          else setSkillsLoadFailed(true);
        }
      })
      .finally(() => {
        if (!cancelled) setServicesLoading(false);
      });
    return () => { cancelled = true; };
  }, [isTechnician, skillsReload]);

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
    if (isTechnician && existing?.member_type !== "technician" && !technicianSeatAvailable) return "Buy an available technician seat before adding a technician. Non-technician staff are free.";
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim() && !phone.trim()) return "Enter an email address or a mobile number.";
    if (isTechnician && servicesLoading) return "Wait for the enabled services to finish loading.";
    if (isTechnician && servicesLoadFailed) return "Enabled services could not be loaded. Close this dialog and try again.";
    if (isTechnician && availableServices.length === 0) return "Configure at least one enabled service before adding a technician.";
    if (isTechnician && availableServices.length > 0 && selectedOfferingIds.length === 0) {
      return "Select at least one service this technician can perform.";
    }
    return null;
  }

  async function handleSave() {
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      if (/full name|email address|mobile number|designation/i.test(invalid)) setActiveSection(0);
      else if (/skill/i.test(invalid)) setActiveSection(2);
      else if (/service/i.test(invalid)) setActiveSection(3);
      return;
    }
    setError(""); setWarning(""); setSaving(true);

    const payload = {
      member_type: memberType as ProviderTeamMember["member_type"],
      full_name: fullName.trim(),
      phone: phone.trim() || null,
      email: email.trim() || null,
      designation: null,
      can_receive_assignment: canReceive,
      // A failed optional-catalog load must not erase an existing selection.
      ...(skillsLoadFailed && isTechnician ? {} : { skill_ids: isTechnician ? selectedSkillIds : [] }),
      supported_offering_ids: isTechnician ? selectedOfferingIds : [],
      profile_photo_url: photoAsset?.preview_url ?? (photoCleared || !isEdit ? null : undefined),
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
          setActivation(await providerTeamMembersApi.generatePassword(memberId));
        } catch (e) {
          problems.push(e instanceof ServiceOSError ? e.message : "login access could not be created");
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

  async function toggleAccess() {
    if (!existing) return;
    const disabling = memberStatus === "active";
    if (disabling && !confirm("Disable this member? They will be signed out and cannot sign in or receive new assignments.")) return;
    setSaving(true); setError("");
    try {
      await (disabling ? providerTeamMembersApi.deactivate(existing.member_id) : providerTeamMembersApi.activate(existing.member_id));
      setMemberStatus(disabling ? "inactive" : "active");
      setActivation(null); setWantsLogin(false);
      setWarning(disabling ? "Member disabled. Login and new assignments are blocked." : "Member enabled. Existing login access is restored unless restricted by an administrator.");
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not change member access.");
    } finally { setSaving(false); }
  }

  async function generateExistingPassword() {
    if (!existing) return;
    if (existing.user_id && !confirm("Generate a replacement password? The previous password will stop working and this member will be signed out.")) return;
    setSaving(true); setError(""); setWarning("");
    try {
      setActivation(await providerTeamMembersApi.generatePassword(existing.member_id));
      setCompleted(true);
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not generate login credentials. Try again.");
    } finally { setSaving(false); }
  }

  return (
    <div
      className="team-member-editor-backdrop"
      role="presentation"
      onMouseDown={event => { if (event.target === event.currentTarget && !saving) onClose(); }}
    >
      <div className="team-member-editor" role="dialog" aria-modal="true" aria-labelledby="team-member-dialog-title">
      <div className="team-member-editor-header">
        <div className="team-member-editor-heading">
          <span className="team-member-editor-avatar">{(fullName || existing?.full_name || "TM").split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase()}</span>
          <span>
            <p>{isEdit ? "Edit team member" : "Add team member"}</p>
            <h2 id="team-member-dialog-title">{fullName || (isEdit ? "Team member" : "New team member")}</h2>
          </span>
        </div>
        <button ref={closeButtonRef} disabled={saving} onClick={onClose} aria-label="Close team member dialog"><X size={17}/></button>
      </div>

      <div className="team-member-editor-body">
        <nav aria-label="Team member sections">
          {EDIT_SECTIONS.map((label, index) => <button type="button" key={label} className={activeSection === index ? "active" : ""} aria-current={activeSection === index ? "step" : undefined} onClick={() => { setError(""); setActiveSection(index); }}><i />{label}</button>)}
        </nav>
        <div className="team-member-editor-content">
          {error && (
            <div role="alert" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>{error}</div>
          )}
          {warning && (
            <div role="alert" style={{ padding: "10px 14px", borderRadius: 8, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", color: "var(--warning-text)", fontSize: 13, marginBottom: 16 }}>{warning}</div>
          )}

          {/* ── Identity ── */}
          {activeSection === 0 && <>
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
          </>}
          {activeSection === 1 && <>
          <SectionTitle>Role &amp; assignment</SectionTitle>
          <p>Only technicians consume paid seats. Staff and managers are free.{!technicianSeatAvailable && existing?.member_type !== "technician" ? " Buy a technician seat on the plan page to unlock the technician role." : ""}</p>
          <Field label="Role" required>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 8 }}>
              {MEMBER_TYPES.map(t => (
                <label key={t.value} style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderRadius: 8, border: `1px solid ${memberType === t.value ? "var(--brand)" : "var(--border)"}`, cursor: "pointer" }}>
                  <input type="radio" disabled={t.value === "technician" && existing?.member_type !== "technician" && !technicianSeatAvailable} checked={memberType === t.value} onChange={() => {
                    setMemberType(t.value);
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
          </>}
          {activeSection === 2 && <>
          <SectionTitle>Approved skills</SectionTitle>
          <Btn variant="secondary" disabled={servicesLoading} onClick={() => setSkillsReload(value => value + 1)}>Refresh skills</Btn>
          {isTechnician && (
            <Field label="Approved skills" hint="Optional tags controlled by the platform administrator for this business category.">
              {servicesLoading ? (
                <p role="status" style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Loading approved skills...</p>
              ) : skillsLoadFailed ? (
                <p role="status" style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Approved skills could not be loaded. You can still save the technician and assign services.</p>
              ) : availableSkills.length === 0 ? (
                <div style={{ padding: 12, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-secondary)", fontSize: 12 }}>
                  No optional skill tags are configured for this category. Service assignments below are enough to add this technician.
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
          {!isTechnician && <p className="team-member-editor-empty">Approved skills only apply to technicians.</p>}
          </>}
          {activeSection === 1 && <>
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
          </>}
          {activeSection === 3 && isTechnician && (
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
          {activeSection === 3 && !isTechnician && <><SectionTitle>Services</SectionTitle><p className="team-member-editor-empty">Service assignments only apply to technicians.</p></>}
          {activeSection === 3 && isTechnician && !isEdit && (
            <>
              <SectionTitle>Weekly availability</SectionTitle>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                This technician automatically follows the business hours in Coverage &amp; availability, including future changes. Each complete two-hour window supports one job per technician, subject to the shared daily limit. Business holidays close booking for everyone.
              </p>
            </>
          )}

          {/* ── Optional login ── */}
          {activeSection === 4 && <>
          <SectionTitle>Login access<Optional/></SectionTitle>
          {isEdit && !completed && <div style={{ marginBottom: 18 }}>
            <p>Team member is {memberStatus === "active" ? "enabled" : "disabled"}. Disabling blocks login and new assignments. Enabling a technician checks your seat plan.</p>
            <Btn variant="secondary" disabled={saving} onClick={toggleAccess}>{memberStatus === "active" ? "Disable member" : "Enable member"}</Btn>
          </div>}
          {isEdit ? <Btn variant="primary" disabled={saving || completed || memberStatus !== "active" || !existing?.email || email.trim().toLowerCase() !== existing.email.toLowerCase()}
            onClick={generateExistingPassword}>{existing?.user_id ? "Regenerate temporary password" : "Generate login password"}</Btn> : <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: hasDeliverableEmail ? "var(--text-primary)" : "var(--text-tertiary)", cursor: hasDeliverableEmail ? "pointer" : "not-allowed" }}>
            <input type="checkbox" checked={wantsLogin} disabled={!hasDeliverableEmail || memberStatus !== "active" || completed || saving}
              onChange={e => setWantsLogin(e.target.checked)}/>
            {existing?.user_id ? "Generate a new temporary password when saving" : "Generate login password so this member can use the app"}
          </label>}
          {isEdit && email !== (existing?.email ?? "") && <p>Save the profile email first, then reopen Manage login to generate credentials.</p>}
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>Use the member's email as their login ID. No email or OTP setup is needed. After saving, copy and share their temporary password privately. They must choose a new password at first login.</p>
          {!hasDeliverableEmail && (
            <p style={{ margin: "6px 0 0 24px", fontSize: 11, color: "var(--text-tertiary)" }}>
              You can add this technician now. Add an email later, then use “Manage login” from the actions menu.
            </p>
          )}
          {activation && <TeamLoginCredentials credentials={activation}/>}

          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 20, padding: "10px 12px", borderRadius: 8, background: "var(--success-bg)", border: "1px solid var(--success-border)" }}>
            <CheckCircle2 size={16} style={{ color: "var(--success)" }}/>
            <span style={{ fontSize: 12, color: "var(--success-text)" }}>Readiness is recalculated automatically after saving.</span>
          </div>
          </>}
        </div>
      </div>

      <div className="team-member-editor-footer">
        <Btn variant="secondary" disabled={saving} onClick={onClose}>Cancel</Btn>
        <div>
          {completed ? (
            <Btn variant="primary" onClick={onSaved}>Done</Btn>
          ) : (
            <>
              {activeSection > 0 && <Btn variant="secondary" disabled={saving} onClick={() => { setError(""); setActiveSection(section => section - 1); }}><ChevronLeft size={14}/> Back</Btn>}
              {activeSection < EDIT_SECTIONS.length - 1
                ? <Btn variant="primary" disabled={saving} onClick={() => { setError(""); setActiveSection(section => section + 1); }}>Continue <ChevronRight size={14}/></Btn>
                : <Btn variant="primary" disabled={saving} onClick={handleSave}>
                    {saving
                      ? <Loader2 size={15} style={{ animation: "spin 0.8s linear infinite" }}/>
                      : <>{isEdit ? "Save changes" : "Add team member"} <CheckCircle2 size={15}/></>}
                  </Btn>}
            </>
          )}
        </div>
      </div>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .team-member-editor-backdrop{position:fixed;inset:0;z-index:1200;display:flex;align-items:center;justify-content:center;padding:20px;background:color-mix(in srgb,var(--text-primary) 12%,transparent);backdrop-filter:blur(7px)}
        .team-member-editor{display:flex;width:min(1040px,calc(100vw - 48px));height:min(760px,88vh);max-height:88vh;flex-direction:column;overflow:hidden;border:1px solid var(--border);border-radius:22px;background:var(--surface);box-shadow:0 30px 70px rgba(24,22,18,.24)}
        .team-member-editor-header{display:flex;min-height:80px;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--border);background:var(--surface)}
        .team-member-editor-heading{display:flex;align-items:center;gap:13px}.team-member-editor-heading>span:last-child{display:flex;flex-direction:column;gap:2px}.team-member-editor-heading p{margin:0;color:var(--text-tertiary);font:500 10px/1.2 "IBM Plex Mono",var(--font-family-mono);letter-spacing:.08em;text-transform:uppercase}.team-member-editor-heading h2{margin:0;color:var(--text-primary);font-size:17px;line-height:1.2}.team-member-editor-avatar{display:grid;width:44px;height:44px;place-items:center;border-radius:50%;background:var(--accent-muted);color:var(--brand);font-size:13px;font-weight:750}.team-member-editor-header>button{display:grid;width:34px;height:34px;place-items:center;border:1px solid var(--border);border-radius:10px;background:var(--surface);color:var(--text-tertiary);cursor:pointer}
        .team-member-editor-body{display:grid;min-height:0;flex:1;grid-template-columns:210px minmax(0,1fr)}.team-member-editor-body>nav{display:flex;flex-direction:column;gap:3px;padding:13px 10px;border-right:1px solid var(--border);background:var(--surface-sunken)}.team-member-editor-body>nav button{display:flex;min-height:38px;align-items:center;gap:10px;padding:0 11px;border:0;border-radius:10px;background:transparent;color:var(--text-tertiary);font:500 12px/1.2 inherit;text-align:left;cursor:pointer}.team-member-editor-body>nav button i{width:7px;height:7px;flex:none;border-radius:50%;background:var(--border)}.team-member-editor-body>nav button.active{background:var(--surface);color:var(--text-primary);font-weight:700;box-shadow:var(--shadow-sm)}.team-member-editor-body>nav button.active i{background:var(--brand)}
        .team-member-editor-content{min-width:0;overflow-y:auto;padding:22px 26px}.team-member-editor-content>h3:first-of-type{margin-top:0!important}.team-member-editor-empty{margin:0;padding:24px;border:1px dashed var(--border);border-radius:12px;color:var(--text-tertiary);font-size:12px;text-align:center}
        .team-member-editor-footer{display:flex;min-height:72px;align-items:center;justify-content:space-between;padding:14px 22px;border-top:1px solid var(--border);background:var(--surface)}.team-member-editor-footer>div{display:flex;gap:9px}
        @media(max-width:900px){.team-member-editor-body{grid-template-columns:190px minmax(0,1fr)}}
        @media(max-width:700px){.team-member-editor{width:calc(100vw - 24px);height:calc(100vh - 24px);max-height:calc(100vh - 24px)}.team-member-editor-body{grid-template-columns:1fr}.team-member-editor-body>nav{flex-direction:row;overflow-x:auto;border-right:0;border-bottom:1px solid var(--border)}.team-member-editor-body>nav button{white-space:nowrap}.team-member-editor-content{padding:20px}.team-member-editor-backdrop{padding:12px}}
      `}</style>
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
const selectStyle: React.CSSProperties = {
  width: "100%", height: 40, padding: "0 12px", fontSize: 13, borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)",
  boxSizing: "border-box", fontFamily: "inherit",
};
