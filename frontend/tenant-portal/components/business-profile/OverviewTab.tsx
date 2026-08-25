"use client";
import React from "react";
import Link from "next/link";
import {
  Lock, CheckCircle2, Circle, IdCard, Building2, FileText, Clock3,
  Wrench, MapPin, Users2, ChevronRight,
} from "lucide-react";
import { Card, Badge } from "../shared/ui";
import type { BusinessProfileOverview } from "../../lib/api";

const LOCKED_FIELDS = new Set(["business_name", "legal_name", "gst_number", "registration_number", "address_line1", "city", "state"]);

function mask(v: string | null, keepStart = 2, keepEnd = 2): string {
  if (!v) return "—";
  if (v.length <= keepStart + keepEnd) return v;
  return v.slice(0, keepStart) + "•".repeat(Math.max(v.length - keepStart - keepEnd, 3)) + v.slice(-keepEnd);
}
function maskEmail(v: string | null): string {
  if (!v || !v.includes("@")) return v || "—";
  const [user, domain] = v.split("@");
  return `${user.slice(0, 2)}${"•".repeat(Math.max(user.length - 2, 2))}@${domain}`;
}

function Field({ label, value, locked }: { label: string; value: string; locked?: boolean }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{label}</span>
        {locked && <Lock size={10} style={{ color: "var(--text-tertiary)" }}/>}
      </div>
      <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, fontWeight: 500 }}>{value || "—"}</p>
    </div>
  );
}

export function OverviewTab({ profile, verifiedLocked }: { profile: BusinessProfileOverview; verifiedLocked: boolean }) {
  const c = profile.completeness;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "68% 32%", gap: 20, alignItems: "flex-start" }}>
      {/* Main column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Business details</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <Field label="Display name" value={profile.business_name ?? ""} locked={verifiedLocked}/>
            <Field label="Legal business name" value={profile.legal_name ?? ""} locked={verifiedLocked}/>
            <Field label="Business type" value={profile.business_type ?? ""}/>
            <Field label="Year established" value={profile.year_established ? String(profile.year_established) : ""}/>
            <Field label="Registration number" value={mask(profile.registration_number)} locked={verifiedLocked}/>
            <Field label="GSTIN / tax identifier" value={mask(profile.gst_number)} locked={verifiedLocked}/>
            <Field label="Primary language" value="English"/>
            <Field label="Registered address" value={[profile.city, profile.state].filter(Boolean).join(", ")} locked={verifiedLocked}/>
          </div>
          {verifiedLocked && (
            <p style={{ fontSize: 11.5, color: "var(--warning-text)", marginTop: 14, marginBottom: 0 }}>
              Verified by ServiceOS · These fields are locked. Change request required.
            </p>
          )}
        </Card>

        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>About the business</p>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
            {profile.description || "No public description added yet."}
          </p>
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Operational summary</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <SummaryStat icon={<Wrench size={16}/>} value={profile.operational_summary.active_services} label="Active services" href="/home-services/services" linkLabel="View in Services & Pricing"/>
            <SummaryStat icon={<MapPin size={16}/>} value={profile.operational_summary.service_areas} label="Coverage pincodes" href="/business/coverage-hours" linkLabel="View Coverage & Hours"/>
            <SummaryStat icon={<Users2 size={16}/>} value={profile.operational_summary.active_technicians} label="Technicians" href="/home-services/team" linkLabel="View in Team Directory"/>
          </div>
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Primary operational contact</p>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--accent-muted)",
                display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", fontWeight: 700, fontSize: 14 }}>
                {(profile.owner_name ?? "?")[0]?.toUpperCase()}
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)" }}>{profile.owner_name ?? "—"}</span>
                  <Badge variant="muted" size="sm">Owner</Badge>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{mask(profile.phone, 2, 4)}</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{maskEmail(profile.email)}</p>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Permissions</p>
              <p style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "4px 0 0", maxWidth: 220 }}>
                This contact manages the business profile and receives critical notifications.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Right column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Profile readiness</p>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 6 }}>
            <ReadinessRing pct={c.percentage}/>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
              {c.completed_requirements.map(key => (
                <span key={key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <CheckCircle2 size={13} style={{ color: "var(--success-text)" }}/> {labelFor(key)}
                </span>
              ))}
              {c.missing_requirements.map(m => (
                <span key={m.key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-tertiary)" }}>
                  <Circle size={13}/> {m.label}
                </span>
              ))}
            </div>
          </div>
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Verification status</p>
          <VerificationRow icon={<IdCard size={14}/>} label="Identity verified" ok={profile.verification_status !== "not_started"}/>
          <VerificationRow icon={<Building2 size={14}/>} label="Business verified" ok={["verified","approved","active"].includes(profile.verification_status)}/>
          <VerificationRow icon={<FileText size={14}/>} label="Documents current" ok={profile.documents.every(d => d.status !== "expired")} okLabel="Current"/>
          <VerificationRow icon={<Clock3 size={14}/>} label="Change requests"
            ok={profile.verification_status !== "changes_pending_review"}
            okLabel="None pending" badLabel="1 pending"/>
        </Card>

        {profile.verification_status === "changes_pending_review" && (
          <Card style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--warning-text)", margin: "0 0 6px" }}>Pending change request</p>
            <p style={{ fontSize: 12, color: "var(--warning-text)", margin: "0 0 8px" }}>
              A change to a verified field has been submitted and is awaiting ServiceOS review.
            </p>
            <Link href="?tab=change-requests" style={{ fontSize: 12, fontWeight: 700, color: "var(--warning-text)" }}>Review request →</Link>
          </Card>
        )}

        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Customer view</p>
          <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 12px", borderRadius: 10, background: "var(--surface-sunken)", marginBottom: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--brand)", color: "#fff",
              display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13 }}>
              {(profile.business_name ?? "?")[0]?.toUpperCase()}
            </div>
            <div>
              <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{profile.business_name}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                {profile.rating.average_rating} ★ ({profile.rating.total_reviews})
              </p>
            </div>
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            Customers see this public profile only after ServiceOS matches your business to their request — never by browsing or choosing a provider directly.
          </p>
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Visibility & privacy</p>
          <PrivacyRow label="Public business details" value="Visible to customers"/>
          <PrivacyRow label="Private legal / owner data" value="Hidden from customers"/>
          <PrivacyRow label="Job-scoped customer access" value="Only for active jobs"/>
        </Card>
      </div>
    </div>
  );
}

function SummaryStat({ icon, value, label, href, linkLabel }: { icon: React.ReactNode; value: number; label: string; href: string; linkLabel: string }) {
  return (
    <div>
      <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--success-bg)", color: "var(--success-text)",
        display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 8 }}>
        {icon}
      </div>
      <p style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{value}</p>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 6px" }}>{label}</p>
      <Link href={href} style={{ fontSize: 11.5, fontWeight: 600, color: "var(--brand)", display: "flex", alignItems: "center", gap: 2 }}>
        {linkLabel} <ChevronRight size={12}/>
      </Link>
    </div>
  );
}

function VerificationRow({ icon, label, ok, okLabel = "Verified", badLabel = "Pending" }: {
  icon: React.ReactNode; label: string; ok: boolean; okLabel?: string; badLabel?: string;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "var(--text-secondary)" }}>{icon} {label}</span>
      <Badge variant={ok ? "success" : "warning"} size="sm">{ok ? okLabel : badLabel}</Badge>
    </div>
  );
}

function PrivacyRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", fontSize: 12 }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ color: "var(--text-tertiary)" }}>{value}</span>
    </div>
  );
}

function ReadinessRing({ pct }: { pct: number }) {
  const r = 30, c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <svg width={76} height={76} viewBox="0 0 76 76" style={{ flexShrink: 0 }}>
      <circle cx={38} cy={38} r={r} fill="none" stroke="var(--surface-sunken)" strokeWidth={8}/>
      <circle cx={38} cy={38} r={r} fill="none" stroke={pct >= 80 ? "var(--success-text)" : "var(--warning-text)"}
        strokeWidth={8} strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 38 38)"/>
      <text x={38} y={43} textAnchor="middle" fontSize={18} fontWeight={800} fill="var(--text-primary)">{pct}%</text>
    </svg>
  );
}

function labelFor(key: string): string {
  const map: Record<string, string> = {
    business_name: "Business Name", phone: "Business Phone", email: "Business Email",
    gst_number: "GST Number", address_line1: "Business Address", city: "City", state: "State",
    logo_url: "Business Logo", description: "Business Description", shop_photo_media_id: "Storefront Photo",
  };
  return map[key] ?? key;
}
