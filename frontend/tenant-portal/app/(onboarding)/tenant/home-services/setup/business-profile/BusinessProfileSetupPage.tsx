"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { TenantLayout } from "../../../../../../components/layout/TenantLayout";
import { ProfilePhotoUploader } from "../../../../../../components/shared/ProfilePhotoUploader";
import { Card, Input, Select, Btn, Badge, Skeleton } from "../../../../../../components/shared/ui";
import { PageHeader, PageShell } from "@serviceos/design-system";
import {
  businessProfileApi, homeServicesSetupOverviewApi, ServiceOSError,
  type BusinessProfile, type BusinessProfileOptions, type MediaAsset,
  type UpdateBusinessProfilePayload,
} from "../../../../../../lib/api";

const SETUP_STEPS = [
  "overview", "business-profile", "documents", "services-pricing",
  "coverage-availability", "staff", "finance", "review",
] as const;
const STEP_NUMBER = SETUP_STEPS.indexOf("business-profile") + 1;
const TOTAL_STEPS = SETUP_STEPS.length;

const EDITABLE_STATUSES = new Set(["draft_setup", "draft", "changes_requested"]);

// Mirrors the backend's BUSINESS_PROFILE readiness gate
// (app/engines/vertical_catalog/home_services_setup_service.py) so the ring
// reflects the same real, persisted fields the setup checklist counts.
const REQUIRED_FIELDS: (keyof BusinessProfile)[] = [
  "business_name", "business_type", "phone", "email", "address_line1", "district", "city", "state", "zipcode",
];

type FormState = {
  business_name: string; legal_name: string; business_type: string;
  registration_number: string; year_established: string;
  phone: string; email: string; website_url: string;
  address_line1: string; address_line2: string; district: string;
  city: string; state: string; zipcode: string; country: string;
  description: string;
};

function profileToForm(p: BusinessProfile): FormState {
  return {
    business_name: p.business_name ?? "", legal_name: p.legal_name ?? "",
    business_type: p.business_type ?? "", registration_number: p.registration_number ?? "",
    year_established: p.year_established ? String(p.year_established) : "",
    phone: p.phone ?? "", email: p.email ?? "", website_url: p.website_url ?? "",
    address_line1: p.address_line1 ?? "", address_line2: p.address_line2 ?? "",
    district: p.district ?? "", city: p.city ?? "", state: p.state ?? "",
    zipcode: p.zipcode ?? "", country: p.country ?? "India",
    description: p.description ?? "",
  };
}

type SaveState = "idle" | "dirty" | "saving" | "saved" | "failed";

function ProfileShell({ mode, children }: { mode: "onboarding" | "workspace"; children: React.ReactNode }) {
  return mode === "workspace"
    ? <TenantLayout activeNav="business-profile"><PageShell>{children}</PageShell></TenantLayout>
    : <OnboardingShell activeNav="business-profile"><PageShell>{children}</PageShell></OnboardingShell>;
}

function BusinessProfileWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const mode: "onboarding" | "workspace" = pathname.startsWith("/profile") ? "workspace" : "onboarding";
  const workspace = mode === "workspace";
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [options, setOptions] = useState<BusinessProfileOptions | null>(null);
  const [verticalStatus, setVerticalStatus] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saving, setSaving] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const savingRef = useRef(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      businessProfileApi.get(),
      businessProfileApi.getOptions(),
      workspace ? Promise.resolve(null) : homeServicesSetupOverviewApi.getOverview().catch(() => null),
    ])
      .then(([p, o, overview]) => {
        setProfile(p);
        setOptions(o);
        setForm(profileToForm(p));
        setVerticalStatus(overview?.vertical.status ?? null);
        setSaveState("idle");
      })
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your business profile."))
      .finally(() => setLoading(false));
  }, [workspace]);

  useEffect(() => { load(); }, [load]);

  // Logo/cover uploads used to call load(), which re-fetched the profile and
  // rebuilt `form` from the server copy -- so picking a logo after typing threw
  // away every field that had not been saved yet, and flipped the whole page
  // back to its loading skeleton. The uploader already persists the image on
  // its own (POST /v1/provider/profile/logo writes tenant.logo_url +
  // business_logo_media_id, and the DELETE clears them), and those fields are
  // not part of UpdateBusinessProfilePayload, so nothing else has to be
  // re-read: patch only the image fields on `profile` and leave `form` --
  // everything the user typed -- untouched for the single Save at the end.
  const patchProfileMedia = useCallback((patch: Partial<BusinessProfile>) => {
    setProfile(p => (p ? { ...p, ...patch } : p));
  }, []);

  const changePending = profile?.verification_status === "changes_pending_review";
  const readOnly = changePending || (!workspace && verticalStatus !== null && !EDITABLE_STATUSES.has(verticalStatus));

  const readiness = useMemo(() => {
    if (!profile) return { percentage: 0, completed: 0, total: REQUIRED_FIELDS.length, missing: [] as string[] };
    const missing = REQUIRED_FIELDS.filter(f => !profile[f]);
    const completed = REQUIRED_FIELDS.length - missing.length;
    return {
      percentage: Math.round((completed / REQUIRED_FIELDS.length) * 100),
      completed, total: REQUIRED_FIELDS.length, missing,
    };
  }, [profile]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm(f => f ? { ...f, [key]: value } : f);
    setSaveState(s => (s === "saved" || s === "idle") ? "dirty" : s);
  }

  function validate(f: FormState): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!f.business_name.trim()) errs.business_name = "Business name is required.";
    if (!f.business_type) errs.business_type = "Select a business type.";
    if (!f.phone.trim()) errs.phone = "Business phone is required.";
    else if (!/^\+?[1-9]\d{7,14}$/.test(f.phone.trim())) errs.phone = "Enter a valid phone number.";
    if (!f.email.trim()) errs.email = "Business email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) errs.email = "Enter a valid email address.";
    if (!f.address_line1.trim()) errs.address_line1 = "Address line 1 is required.";
    if (!f.district.trim()) errs.district = "Locality/area is required.";
    if (!f.city.trim()) errs.city = "City is required.";
    if (!f.state) errs.state = "Select a state.";
    if (!f.zipcode.trim()) errs.zipcode = "Pincode is required.";
    else if (!/^\d{6}$/.test(f.zipcode.trim())) errs.zipcode = "Pincode must be exactly 6 digits.";
    if (f.year_established) {
      const y = Number(f.year_established);
      const currentYear = new Date().getFullYear();
      if (!Number.isInteger(y) || y < 1800 || y > currentYear) errs.year_established = `Enter a year between 1800 and ${currentYear}.`;
    }
    if (f.website_url && !/^https?:\/\/.+/.test(f.website_url.trim())) errs.website_url = "Website must start with http:// or https://";
    return errs;
  }

  function buildPayload(f: FormState): UpdateBusinessProfilePayload {
    return {
      business_name: f.business_name.trim(),
      legal_name: f.legal_name.trim() || undefined,
      business_type: f.business_type || undefined,
      registration_number: f.registration_number.trim() || undefined,
      year_established: f.year_established ? Number(f.year_established) : undefined,
      phone: f.phone.trim(),
      email: f.email.trim(),
      website_url: f.website_url.trim() || undefined,
      address_line1: f.address_line1.trim(),
      address_line2: f.address_line2.trim() || undefined,
      district: f.district.trim(),
      city: f.city.trim(),
      state: f.state,
      zipcode: f.zipcode.trim(),
      country: f.country || "India",
      description: f.description.trim() || undefined,
    };
  }

  async function handleSaveDraft() {
    if (!form || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setSaveState("saving");
    try {
      // Draft save persists whatever is filled in without full-page validation.
      const payload: UpdateBusinessProfilePayload = {};
      const full = buildPayload(form);
      (Object.keys(full) as (keyof UpdateBusinessProfilePayload)[]).forEach(k => {
        const v = form[k as keyof FormState];
        if (v) (payload as Record<string, unknown>)[k] = full[k];
      });
      const updated = await businessProfileApi.update(payload);
      setProfile(updated);
      setSaveState("saved");
    } catch (e) {
      setSaveState("failed");
      setError(e instanceof ServiceOSError ? e.message : "Could not save draft.");
    } finally {
      setSaving(false);
      savingRef.current = false;
    }
  }

  async function handleSaveAndContinue() {
    if (!form || savingRef.current) return;
    const errs = validate(form);
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) return;
    savingRef.current = true;
    setSaving(true);
    setSaveState("saving");
    try {
      const updated = await businessProfileApi.update(buildPayload(form));
      setProfile(updated);
      setSaveState("saved");
      if (workspace) {
        setSubmissionMessage(updated.reverification_triggered
          ? "Your protected changes were sent to Fuvay for review. Your current approved details stay published until fresh documents are uploaded and an admin approves the request."
          : "Your business profile changes are now saved.");
        load();
      } else {
        router.push("/tenant/home-services/setup/documents");
      }
    } catch (e) {
      setSaveState("failed");
      setError(e instanceof ServiceOSError ? e.message : "Could not save your business profile.");
    } finally {
      setSaving(false);
      savingRef.current = false;
    }
  }

  function handleBack() {
    if (saveState === "dirty" && !window.confirm("You have unsaved changes. Leave without saving?")) return;
    router.push(workspace ? "/dashboard" : "/tenant/home-services/setup/overview");
  }

  if (loading) {
    return (
      <ProfileShell mode={mode}>
        <PageHeader title="Business profile" description={workspace ? "Manage the business identity, contact and address information approved during setup." : "Tell us about your business. These details will be reviewed before your workspace is activated."} />
        <Skeleton height={12} style={{ marginBottom: 20 }}/>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))", gap: 20 }}>
          <Skeleton height={520}/>
          <Skeleton height={520}/>
        </div>
      </ProfileShell>
    );
  }

  if (error && !profile) {
    return (
      <ProfileShell mode={mode}>
        <PageHeader title="Business profile" description={workspace ? "Manage the business identity, contact and address information approved during setup." : "Tell us about your business. These details will be reviewed before your workspace is activated."} />
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your business profile.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </ProfileShell>
    );
  }

  if (!form || !profile) return null;

  const entityTypeOptions = (options?.entity_types ?? []).map(t => ({ value: t.value, label: t.label }));
  const stateOptions = (options?.states ?? []).map(s => ({ value: s, label: s }));

  const saveBadge = {
    idle: { label: "Draft saved", variant: "success" as const, icon: <CheckCircle2 size={13}/> },
    dirty: { label: "Unsaved changes", variant: "warning" as const, icon: <AlertCircle size={13}/> },
    saving: { label: "Saving…", variant: "muted" as const, icon: <Loader2 size={13} style={{ animation: "spin 0.7s linear infinite" }}/> },
    saved: { label: "Draft saved", variant: "success" as const, icon: <CheckCircle2 size={13}/> },
    failed: { label: "Save failed", variant: "danger" as const, icon: <XCircle size={13}/> },
  }[saveState];

  return (
    <ProfileShell mode={mode}>
      <PageHeader
        eyebrow={workspace ? "Business profile" : `Tenant onboarding · Step ${STEP_NUMBER} of ${TOTAL_STEPS}`}
        title="Business profile"
        description={workspace
          ? "Manage the same business identity, contact and address information approved during setup."
          : "Tell us about your business. These details will be reviewed before your workspace is activated."}
        actions={<Badge variant={saveBadge.variant} size="lg">{saveBadge.icon}{saveBadge.label}</Badge>}
      />

      {!workspace && <div className="biz-profile-progress" aria-label={`Setup step ${STEP_NUMBER} of ${TOTAL_STEPS}`}><span style={{ width: `${STEP_NUMBER / TOTAL_STEPS * 100}%` }} /></div>}

      {submissionMessage && (
        <div role="status" style={{ padding: "12px 16px", marginBottom: 20, background: "var(--success-bg)", border: "1px solid var(--success-border)", borderRadius: "var(--radius-lg)", color: "var(--success-text)", fontSize: 13 }}>
          {submissionMessage}
        </div>
      )}

      {readOnly && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", marginBottom: 20,
          background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: "var(--radius-lg)",
        }}>
          <ShieldCheck size={16} style={{ color: "var(--info-text)", flexShrink: 0 }}/>
          <p style={{ fontSize: 13, color: "var(--info-text)", margin: 0 }}>
            {changePending
              ? "A protected profile change is awaiting review. Upload the requested verification documents, then Fuvay can approve and publish it."
              : `This section is read-only while Home Services is ${verticalStatus?.replace(/_/g, " ")}. Contact support if you need to make a correction.`}
          </p>
        </div>
      )}

      <style>{`
        .biz-profile-progress{height:5px;margin:-2px 0 16px;overflow:hidden;border-radius:999px;background:var(--surface-sunken)}.biz-profile-progress span{display:block;height:100%;border-radius:inherit;background:var(--brand)}
        .biz-profile-grid { display: grid; grid-template-columns: minmax(0,1.7fr) minmax(320px,1fr); gap: 16px; align-items: start; }
        @media (max-width: 900px) { .biz-profile-grid { grid-template-columns: 1fr; } }
        .biz-profile-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .biz-profile-half { width: calc(50% - 8px); }
        .biz-profile-section-title { font-size: 16px; font-weight: 700; margin: 0 0 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
        .biz-profile-address-head { margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
        .biz-profile-address-head h2 { font-size: 16px; font-weight: 700; margin: 0 0 5px; color: var(--text-primary); }
        .biz-profile-address-head p { font-size: 12px; color: var(--text-tertiary); margin: 0; }
        @media (max-width: 560px) { .biz-profile-row2 { grid-template-columns: 1fr; } .biz-profile-half { width: 100%; } }
      `}</style>

      <div className="biz-profile-grid">
        <fieldset disabled={readOnly} style={{ border: "none", padding: 0, margin: 0, minWidth: 0 }}>
          <Card style={{ marginBottom: 16 }}>
            <h2 className="biz-profile-section-title">Business details</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="biz-profile-half">
                <Input label="Business name" required value={form.business_name}
                  onChange={v => set("business_name", v)} error={fieldErrors.business_name}
                  placeholder="Public, customer-facing name"/>
              </div>
              <div className="biz-profile-row2">
                <Input label="Registration number (optional)" value={form.registration_number}
                  onChange={v => set("registration_number", v)} placeholder="e.g. CIN, if applicable"/>
                <Input label="Year established (optional)" type="number" value={form.year_established}
                  onChange={v => set("year_established", v)} error={fieldErrors.year_established}
                  placeholder="e.g. 2015"/>
              </div>
              <div className="biz-profile-row2">
                <Input label="Business email" required type="email" value={form.email}
                  onChange={v => set("email", v)} error={fieldErrors.email}
                  hint="May differ from your login email" placeholder="business@example.com"/>
                <Input label="Business phone" required value={form.phone}
                  onChange={v => set("phone", v)} error={fieldErrors.phone}
                  placeholder="+91XXXXXXXXXX"/>
              </div>
              <Input label="Website (optional)" value={form.website_url}
                onChange={v => set("website_url", v)} error={fieldErrors.website_url}
                placeholder="https://"/>

              <div className="biz-profile-row2"><span/><Select label="Business type" value={form.business_type}
                onChange={v => set("business_type", v)} options={entityTypeOptions}
                placeholder="Select business type"/></div>

            </div>
          </Card>

          <Card>
            <div className="biz-profile-address-head">
              <h2>Registered address</h2>
              <p>
                This is your business&apos;s legal/compliance address, not your service coverage area — you&apos;ll set where your team works in Coverage &amp; Availability.
              </p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Input label="Address line 1" required value={form.address_line1}
                onChange={v => set("address_line1", v)} error={fieldErrors.address_line1}
                placeholder="House no., building, street name"/>
              <Input label="Address line 2 (optional)" value={form.address_line2}
                onChange={v => set("address_line2", v)} placeholder="Landmark, area"/>
              <div className="biz-profile-row2">
                <Input label="Locality / area" required value={form.district}
                  onChange={v => set("district", v)} error={fieldErrors.district}
                  placeholder="Enter locality"/>
                <Input label="City" required value={form.city}
                  onChange={v => set("city", v)} error={fieldErrors.city} placeholder="Enter city"/>
              </div>
              <div className="biz-profile-row2">
                <Select label="State" value={form.state} onChange={v => set("state", v)}
                  options={stateOptions} placeholder="Select state"/>
                <Input label="Pincode" required value={form.zipcode}
                  onChange={v => set("zipcode", v)} error={fieldErrors.zipcode} placeholder="Enter pincode"/>
              </div>
            </div>
          </Card>
        </fieldset>

        <div style={{ minWidth: 0 }}>
          <Card style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Profile readiness</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{
                width: 64, height: 64, borderRadius: "50%", flexShrink: 0,
                background: `conic-gradient(var(--brand) ${readiness.percentage * 3.6}deg, var(--surface-sunken) 0deg)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <div style={{
                  width: 50, height: 50, borderRadius: "50%", background: "var(--surface)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                }}>{readiness.percentage}%</div>
              </div>
              <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, flex: 1 }}>
                Complete your profile to activate your workspace.
              </p>
            </div>
            <ul style={{ listStyle: "none", margin: "14px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { label: "Business name", done: !!profile.business_name },
                { label: "Business type", done: !!profile.business_type },
                { label: "Business contact", done: !!profile.phone && !!profile.email },
                { label: "Registered address", done: !!profile.address_line1 && !!profile.city && !!profile.state },
              ].map(item => (
                <li key={item.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                  {item.done
                    ? <CheckCircle2 size={15} style={{ color: "var(--success-text)", flexShrink: 0 }}/>
                    : <span style={{ width: 15, height: 15, borderRadius: "50%", border: "1px solid var(--border-strong)", flexShrink: 0 }}/>}
                  <span style={{ color: item.done ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                    {item.label}
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px", color: "var(--text-primary)" }}>Why we need this</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 10px" }}>
              {workspace
                ? "Protected identity fields create an admin-reviewed change request. They never replace your published details immediately."
                : "This information helps us verify your business and is reviewed by our team before your workspace is activated."}
            </p>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              It is stored securely and is not shown publicly except for the specific fields your customers see.
            </p>
          </Card>

          <Card>
            <h2 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>Business identity</h2>
            <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 8px" }}>Business logo</p>
            <ProfilePhotoUploader
              ownerType="provider_business"
              currentMediaId={profile.business_logo_media_id}
              currentPreviewUrl={profile.logo_url}
              displayName={profile.business_name}
              disabled={readOnly}
              onUploaded={(asset: MediaAsset) => patchProfileMedia({
                business_logo_media_id: asset.id,
                logo_url: asset.preview_url ?? asset.public_url ?? null,
              })}
              onRemoved={() => patchProfileMedia({ business_logo_media_id: null, logo_url: null })}
            />
            {/* The optional cover/shop image was removed from this step at
                explicit request (2026-09-03). The logo is the only identity
                image a provider sets here. */}
          </Card>
        </div>
      </div>

      <div style={{
        position: "sticky", bottom: 0, marginTop: 24, padding: "16px 20px",
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)",
        display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap",
      }}>
        <Btn variant="secondary" onClick={handleBack}>Back</Btn>
        {!readOnly && (
          <>
            {!workspace && <Btn variant="secondary" loading={saving} onClick={handleSaveDraft}>Save draft</Btn>}
            <Btn variant="primary" loading={saving} onClick={handleSaveAndContinue}>{workspace ? "Save profile changes" : "Save & continue"}</Btn>
          </>
        )}
      </div>
    </ProfileShell>
  );
}

export default function BusinessProfilePage() {
  return <BusinessProfileWorkspace/>;
}
