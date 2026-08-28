"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Building2,
  Clock3,
  Globe2,
  IdCard,
  Image as ImageIcon,
  Mail,
  MapPin,
  Pencil,
  Phone,
  RefreshCw,
  ShieldCheck,
  Users2,
  Wrench,
} from "lucide-react";
import BusinessProfileWorkspace from "../../(onboarding)/tenant/home-services/setup/business-profile/page";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { resolveMediaUrl } from "../../../components/shared/ProfilePhotoUploader";
import { Badge, Btn, Card, KpiGrid, Skeleton, SummaryCard } from "../../../components/shared/ui";
import { businessProfileApi, ServiceOSError, type BusinessProfile, type BusinessProfileOverview } from "../../../lib/api";

function normalizeProfile(profile: BusinessProfile): BusinessProfileOverview {
  return {
    ...profile,
    completeness: profile.completeness ?? {
      percentage: 0,
      completed_count: 0,
      total_count: 0,
      completed_requirements: [],
      missing_requirements: [],
    },
    operational_summary: profile.operational_summary ?? {
      active_services: 0,
      service_areas: 0,
      active_technicians: 0,
    },
    rating: profile.rating ?? { average_rating: 0, total_reviews: 0 },
    documents: profile.documents ?? [],
  };
}

function initials(name?: string | null) {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  return (parts.length ? parts.map(part => part[0]).join("").slice(0, 2) : "?").toUpperCase();
}

function display(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function mask(value?: string | null, start = 2, end = 2) {
  if (!value) return "-";
  if (value.length <= start + end) return value;
  return `${value.slice(0, start)}${"*".repeat(Math.max(value.length - start - end, 4))}${value.slice(-end)}`;
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

function verificationBadge(status: string) {
  if (["verified", "approved", "active"].includes(status)) return <Badge variant="success">Verified</Badge>;
  if (["pending", "changes_pending_review"].includes(status)) return <Badge variant="warning">{statusLabel(status)}</Badge>;
  if (status === "rejected") return <Badge variant="danger">Rejected</Badge>;
  return <Badge variant="muted">{statusLabel(status || "not started")}</Badge>;
}

function Field({ label, value, icon, protectedField }: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  protectedField?: boolean;
}) {
  return (
    <div className="profile-read-field">
      <div className="profile-read-field-label">
        {icon}
        <span>{label}</span>
        {protectedField && <ShieldCheck size={12}/>}
      </div>
      <div className="profile-read-field-value">{value || "-"}</div>
    </div>
  );
}

export default function BusinessProfilePage() {
  return (
    <Suspense fallback={<BusinessProfileSkeletonPage/>}>
      <BusinessProfileRoute/>
    </Suspense>
  );
}

function BusinessProfileRoute() {
  const searchParams = useSearchParams();
  const editMode = searchParams.get("mode") === "edit";

  if (editMode) {
    return <BusinessProfileWorkspace/>;
  }

  return <BusinessProfileReadOnly/>;
}

function BusinessProfileSkeletonPage() {
  return (
    <TenantLayout activeNav="business-profile">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <Skeleton height={260}/>
        <KpiGrid minCardWidth={190}>
          <Skeleton height={104}/>
          <Skeleton height={104}/>
          <Skeleton height={104}/>
          <Skeleton height={104}/>
        </KpiGrid>
      </div>
    </TenantLayout>
  );
}

function BusinessProfileReadOnly() {
  const router = useRouter();
  const [profile, setProfile] = useState<BusinessProfileOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    businessProfileApi.get()
      .then(profileData => setProfile(normalizeProfile(profileData)))
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "Could not load business profile."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const coverUrl = resolveMediaUrl(profile?.shop_photo_url);
  const logoUrl = resolveMediaUrl(profile?.logo_url);
  const verifiedLocked = !!profile && ["verified", "approved", "active", "changes_pending_review"].includes(profile.verification_status);

  // The provider does not manage documents day to day -- approval verifies the
  // business and the Verified badge is what they see for it. The only thing
  // still worth surfacing is a document that needs THEIR action: rejected, or
  // expired. Bookability blocks on both, so with no route to fix one the
  // provider would be stuck with no way back.
  const documentsNeedingAction = useMemo(() => {
    const now = Date.now();
    return (profile?.documents ?? []).filter(doc =>
      doc.status === "rejected"
      || (doc.expiry_date ? new Date(doc.expiry_date).getTime() < now : false));
  }, [profile]);

  return (
    <TenantLayout activeNav="business-profile">
      <style>{`
        .profile-read-wrap { display: flex; flex-direction: column; gap: 20px; }
        .profile-read-cover { height: 224px; position: relative; overflow: hidden; background:
          radial-gradient(circle at 18% 18%, color-mix(in srgb, var(--brand) 28%, transparent), transparent 34%),
          linear-gradient(135deg, var(--surface-sunken), var(--surface), color-mix(in srgb, var(--brand) 12%, var(--surface-sunken))); }
        .profile-read-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .profile-read-cover-shade { position: absolute; inset: 0; background: linear-gradient(180deg, transparent 20%, rgba(0,0,0,.42)); }
        .profile-read-identity { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 18px; align-items: end; padding: 0 24px 24px; margin-top: -46px; position: relative; z-index: 1; }
        .profile-read-logo { width: 96px; height: 96px; border-radius: 20px; overflow: hidden; border: 4px solid var(--surface); background: var(--brand); color: white; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 800; box-shadow: var(--shadow-md); }
        .profile-read-logo img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .profile-read-title h1 { margin: 0; color: var(--text-primary); font-size: 28px; font-weight: 800; letter-spacing: 0; }
        .profile-read-title p { margin: 6px 0 0; color: var(--text-secondary); font-size: 14px; max-width: 760px; line-height: 1.55; }
        .profile-read-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
        .profile-read-body { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(320px, .75fr); gap: 20px; align-items: start; }
        .profile-read-card-title { margin: 0 0 16px; color: var(--text-primary); font-size: 15px; font-weight: 800; }
        .profile-read-field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
        .profile-read-field { min-width: 0; padding: 12px 0; border-bottom: 1px solid var(--border); }
        .profile-read-field-label { display: flex; align-items: center; gap: 6px; color: var(--text-tertiary); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 5px; }
        .profile-read-field-value { color: var(--text-primary); font-size: 13.5px; font-weight: 600; line-height: 1.45; overflow-wrap: anywhere; }
        .profile-read-document-row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
        .profile-read-status-box { display: flex; gap: 10px; align-items: flex-start; padding: 14px 16px; border-radius: var(--radius-lg); border: 1px solid var(--warning-border); background: var(--warning-bg); color: var(--warning-text); }
        .profile-read-action-stack { display: flex; flex-direction: column; gap: 10px; }
        @media (max-width: 980px) {
          .profile-read-body { grid-template-columns: 1fr; }
          .profile-read-identity { grid-template-columns: auto 1fr; }
          .profile-read-actions { grid-column: 1 / -1; justify-self: stretch; }
        }
        @media (max-width: 640px) {
          .profile-read-cover { height: 168px; }
          .profile-read-identity { padding: 0 16px 18px; gap: 12px; }
          .profile-read-logo { width: 76px; height: 76px; border-radius: 16px; font-size: 24px; }
          .profile-read-title h1 { font-size: 22px; }
          .profile-read-field-grid { grid-template-columns: 1fr; }
        }
      `}</style>

      {loading && (
        <div className="profile-read-wrap">
          <Skeleton height={260}/>
          <KpiGrid minCardWidth={190}>
            <Skeleton height={104}/>
            <Skeleton height={104}/>
            <Skeleton height={104}/>
            <Skeleton height={104}/>
          </KpiGrid>
          <div className="profile-read-body">
            <Skeleton height={460}/>
            <Skeleton height={460}/>
          </div>
        </div>
      )}

      {!loading && error && (
        <Card>
          <div role="alert" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <AlertCircle size={20} style={{ color: "var(--danger-text)" }}/>
              <div>
                <p style={{ margin: 0, color: "var(--text-primary)", fontWeight: 800 }}>Business profile could not load</p>
                <p style={{ margin: "4px 0 0", color: "var(--text-secondary)", fontSize: 13 }}>{error}</p>
              </div>
            </div>
            <Btn variant="secondary" icon={<RefreshCw size={15}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      )}

      {!loading && profile && (
        <div className="profile-read-wrap">
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <div>
              <p style={{ margin: "0 0 4px", color: "var(--brand)", fontSize: 11, fontWeight: 800, letterSpacing: ".08em" }}>BUSINESS</p>
              <h1 style={{ margin: 0, color: "var(--text-primary)", fontSize: 24, fontWeight: 800 }}>Business Profile</h1>
              <p style={{ margin: "6px 0 0", color: "var(--text-secondary)", fontSize: 14 }}>
                Approved identity, public presentation, verification status, and operating summary.
              </p>
            </div>
            <Btn variant="primary" icon={<Pencil size={15}/>} onClick={() => router.push("/profile?mode=edit")}>
              Edit profile
            </Btn>
          </div>

          <Card padding={0} style={{ overflow: "hidden" }}>
            <div className="profile-read-cover">
              {coverUrl ? <img src={coverUrl} alt="" /> : <ImageIcon size={38} style={{ position: "absolute", right: 28, top: 28, color: "var(--text-tertiary)", opacity: .55 }}/>}
              <div className="profile-read-cover-shade"/>
            </div>
            <div className="profile-read-identity">
              <div className="profile-read-logo">
                {logoUrl ? <img src={logoUrl} alt="" /> : initials(profile.business_name)}
              </div>
              <div className="profile-read-title">
                <h1>{display(profile.business_name)}</h1>
                <p>{profile.description || "No public business description has been added yet."}</p>
                <div className="profile-read-badges">
                  {verificationBadge(profile.verification_status)}
                  <Badge variant={profile.status === "active" ? "success" : "muted"}>{statusLabel(profile.status)}</Badge>
                  <Badge variant="info">Home Services</Badge>
                  {verifiedLocked && <Badge variant="warning">Protected fields require review</Badge>}
                </div>
              </div>
              <div className="profile-read-actions">
                <div style={{ textAlign: "right" }}>
                  <p style={{ margin: 0, color: "var(--text-tertiary)", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em" }}>Completeness</p>
                  <p style={{ margin: "3px 0", color: "var(--text-primary)", fontSize: 30, fontWeight: 800 }}>{profile.completeness.percentage}%</p>
                  <div style={{ width: 160, maxWidth: "100%", height: 7, borderRadius: 999, background: "var(--surface-sunken)", overflow: "hidden", border: "1px solid var(--border)" }}>
                    <div style={{ width: `${profile.completeness.percentage}%`, height: "100%", background: profile.completeness.percentage >= 80 ? "var(--success-text)" : "var(--brand)" }}/>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {profile.verification_status === "changes_pending_review" && (
            <div className="profile-read-status-box">
              <Clock3 size={17} style={{ flexShrink: 0, marginTop: 2 }}/>
              <div>
                <p style={{ margin: "0 0 3px", fontWeight: 800 }}>Profile change is under admin review</p>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>
                  Your approved profile remains live while the requested protected-field change is reviewed.
                </p>
              </div>
            </div>
          )}

          <KpiGrid minCardWidth={190}>
            <SummaryCard label="Active services" value={profile.operational_summary.active_services} sub="Published offerings" icon={<Wrench/>} tone="success" onClick={() => router.push("/home-services/services")}/>
            <SummaryCard label="Coverage pincodes" value={profile.operational_summary.service_areas} sub="Bookable service areas" icon={<MapPin/>} tone="info" onClick={() => router.push("/business/coverage-hours")}/>
            <SummaryCard label="Technicians" value={profile.operational_summary.active_technicians} sub="Active team members" icon={<Users2/>} tone="success" onClick={() => router.push("/home-services/team")}/>
          </KpiGrid>

          <div className="profile-read-body">
            <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
              <Card>
                <p className="profile-read-card-title">Business identity</p>
                <div className="profile-read-field-grid">
                  <Field label="Display name" value={display(profile.business_name)} icon={<Building2 size={13}/>} protectedField={verifiedLocked}/>
                  <Field label="Legal name" value={display(profile.legal_name)} icon={<IdCard size={13}/>} protectedField={verifiedLocked}/>
                  <Field label="Business type" value={display(profile.business_type)} protectedField={verifiedLocked}/>
                  <Field label="Year established" value={display(profile.year_established)}/>
                  <Field label="Registration number" value={mask(profile.registration_number)} protectedField={verifiedLocked}/>
                  <Field label="GSTIN / tax identity" value={mask(profile.gst_number)} protectedField={verifiedLocked}/>
                </div>
              </Card>

              <Card>
                <p className="profile-read-card-title">Contact and registered address</p>
                <div className="profile-read-field-grid">
                  <Field label="Business phone" value={display(profile.phone)} icon={<Phone size={13}/>}/>
                  <Field label="Business email" value={display(profile.email)} icon={<Mail size={13}/>}/>
                  <Field label="Website" value={profile.website_url ? <a href={profile.website_url} target="_blank" rel="noreferrer" style={{ color: "var(--brand)", textDecoration: "none" }}>{profile.website_url}</a> : "-"} icon={<Globe2 size={13}/>}/>
                  <Field label="Owner" value={display(profile.owner_name)}/>
                  <Field label="Registered address" value={[profile.address_line1, profile.address_line2, profile.district, profile.city, profile.state, profile.zipcode].filter(Boolean).join(", ")} icon={<MapPin size={13}/>} protectedField={verifiedLocked}/>
                  <Field label="Country" value={display(profile.country)}/>
                </div>
              </Card>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
              <Card>
                <p className="profile-read-card-title">Verification</p>
                <div className="profile-read-action-stack">
                  <Field label="Current status" value={verificationBadge(profile.verification_status)}/>
                  <Field label="Customer rating" value={`${profile.rating.average_rating.toFixed(1)} (${profile.rating.total_reviews} reviews)`}/>
                  <Field label="Created" value={profile.created_at ? new Date(profile.created_at).toLocaleDateString() : "-"}/>
                </div>
              </Card>

              {documentsNeedingAction.length > 0 && (
                <Card>
                  <p className="profile-read-card-title" style={{ margin: "0 0 8px" }}>Action needed</p>
                  <p style={{ margin: "0 0 10px", color: "var(--text-secondary)", fontSize: 13 }}>
                    {documentsNeedingAction.length} verification document{documentsNeedingAction.length === 1 ? " needs" : "s need"} replacing.
                    New bookings are paused until {documentsNeedingAction.length === 1 ? "it is" : "they are"} current again.
                  </p>
                  {documentsNeedingAction.map(doc => (
                    <div key={doc.id} className="profile-read-document-row">
                      <div style={{ minWidth: 0 }}>
                        <p style={{ margin: 0, color: "var(--text-primary)", fontSize: 13, fontWeight: 700 }}>{doc.label || doc.doc_type}</p>
                        <p style={{ margin: "3px 0 0", color: "var(--text-tertiary)", fontSize: 11 }}>{doc.doc_type.replace(/_/g, " ")}</p>
                      </div>
                      <Badge variant="danger">{doc.status === "rejected" ? "Rejected" : "Expired"}</Badge>
                    </div>
                  ))}
                  <Link href="/documents" style={{ display: "inline-block", marginTop: 10, color: "var(--brand)", fontSize: 12, fontWeight: 800, textDecoration: "none" }}>Replace document</Link>
                </Card>
              )}

              <Card>
                <p className="profile-read-card-title">Edit policy</p>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <ShieldCheck size={17} style={{ color: "var(--brand)", marginTop: 2, flexShrink: 0 }}/>
                  <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.6 }}>
                    Trading fields save normally. Legal name, registered identity, GSTIN, and registered address are staged for admin approval after verification.
                  </p>
                </div>
                <div style={{ marginTop: 14 }}>
                  <Btn variant="secondary" icon={<Pencil size={14}/>} onClick={() => router.push("/profile?mode=edit")}>Edit profile</Btn>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </TenantLayout>
  );
}
