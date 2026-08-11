"use client";
/**
 * Business Profile.
 *
 * This route previously served a ~1100-line page that re-implemented the whole
 * profile inline -- its own hero, its own completion ring, its own "Customer view"
 * and "Visibility & privacy" cards. Meanwhile the built-to-design components in
 * components/business-profile/ (ProfileHero, OverviewTab, PublicProfileTab,
 * LegalVerificationTab, MediaTab) were imported by nothing at all. The page that
 * was supposed to assemble them had never been written, so the older duplicate
 * kept rendering and looked like the design had simply not been applied.
 *
 * This is that missing page. The components are unchanged; they finally have a
 * route. The old inline implementation is gone rather than left beside them,
 * because two pages for one profile is how this drifted apart in the first place.
 *
 * Data comes from GET /v1/provider/business-profile, which now returns the
 * completeness / operational_summary / rating / documents the components read.
 * That percentage is computed server-side from the same eleven checks the old
 * page counted in the browser, so the number has not changed -- only who decides it.
 */
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Skeleton, Card, Btn, Badge } from "../../../components/shared/ui";
import { businessProfileApi, type BusinessProfileOverview } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { ExternalLink, AlertTriangle, Mail, Phone, ShieldCheck, ArrowRight } from "lucide-react";
import { ProfileHero } from "../../../components/business-profile/ProfileHero";
import { OverviewTab } from "../../../components/business-profile/OverviewTab";
import { PublicProfileTab } from "../../../components/business-profile/PublicProfileTab";
import { LegalVerificationTab } from "../../../components/business-profile/LegalVerificationTab";
import { MediaTab } from "../../../components/business-profile/MediaTab";

type TabKey = "overview" | "public" | "legal" | "contacts" | "media" | "change-requests" | "activity";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview",        label: "Overview" },
  { key: "public",          label: "Public Profile" },
  { key: "legal",           label: "Legal & Verification" },
  { key: "contacts",        label: "Contacts" },
  { key: "media",           label: "Media" },
  { key: "change-requests", label: "Change Requests" },
  { key: "activity",        label: "Activity & Audit" },
];

/** Verified fields are locked and need a change request. The tenant is the authority
 *  on that, not the page -- these are the states where ServiceOS has signed off. */
const VERIFIED_STATES = ["verified", "approved", "changes_pending_review"];

export default function BusinessProfilePage() {
  const [tab, setTab] = useState<TabKey>("overview");

  const profileApi = useApi(
    useCallback(() => businessProfileApi.get() as Promise<BusinessProfileOverview>, []),
    [],
  );
  const profile = profileApi.data;

  return (
    <TenantLayout activeNav="business-profile">
      <div style={{ padding: "22px 26px 40px", maxWidth: 1560, margin: "0 auto" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 6px" }}>
          <span style={{ color: "var(--brand)" }}>Business</span> / Business Profile
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Business Profile
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Manage your verified business identity and customer-facing profile.
            </p>
          </div>
        </div>

        {profileApi.loading ? (
          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 16 }}>
            <Skeleton height={190}/>
            <Skeleton height={360}/>
          </div>
        ) : profileApi.error || !profile ? (
          <Card style={{ marginTop: 20 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <AlertTriangle size={16} style={{ color: "var(--danger-text)", marginTop: 2 }}/>
              <div>
                <p style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                  Couldn&apos;t load your business profile
                </p>
                <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                  {profileApi.error ?? "No profile was returned."}
                </p>
                <Btn variant="secondary" size="sm" onClick={profileApi.refetch}>Retry</Btn>
              </div>
            </div>
          </Card>
        ) : (
          <>
            <div style={{ marginTop: 18 }}>
              <ProfileHero
                profile={profile}
                onPreview={() => setTab("public")}
                onEdit={() => setTab("legal")}
              />
            </div>

            <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "18px 0 20px", overflowX: "auto" }}>
              {TABS.map(t => (
                <button key={t.key} onClick={() => setTab(t.key)}
                  style={{
                    padding: "10px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer",
                    background: "none", border: "none", whiteSpace: "nowrap", fontFamily: "inherit",
                    color: tab === t.key ? "var(--brand)" : "var(--text-secondary)",
                    borderBottom: `2px solid ${tab === t.key ? "var(--brand)" : "transparent"}`,
                    marginBottom: -1,
                  }}>
                  {t.label}
                </button>
              ))}
            </div>

            {tab === "overview" && (
              <OverviewTab profile={profile} verifiedLocked={VERIFIED_STATES.includes(profile.verification_status)}/>
            )}
            {tab === "public" && <PublicProfileTab profile={profile} onSaved={profileApi.refetch}/>}
            {tab === "legal" && <LegalVerificationTab profile={profile}/>}
            {tab === "media" && <MediaTab profile={profile} onChanged={profileApi.refetch}/>}
            {tab === "contacts" && <ContactsTab profile={profile}/>}
            {tab === "change-requests" && <ChangeRequestsTab profile={profile}/>}
            {tab === "activity" && <ActivityTab/>}
          </>
        )}
      </div>
    </TenantLayout>
  );
}

/** The one contact ServiceOS holds for this business. There is a single owner contact
 *  on the tenant record -- no contacts table -- so this shows that, rather than an
 *  empty list implying more could be added here. */
function ContactsTab({ profile }: { profile: BusinessProfileOverview }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "68% 32%", gap: 20, alignItems: "flex-start" }}>
      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>
          Primary operational contact
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--accent-muted)",
            color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: 15 }}>
            {(profile.owner_name ?? profile.business_name ?? "?")[0]?.toUpperCase()}
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                {profile.owner_name ?? "Not set"}
              </span>
              <Badge variant="muted" size="sm">Owner</Badge>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "3px 0 0" }}>
              This contact manages the business profile and receives critical notifications.
            </p>
          </div>
        </div>
        <ContactRow icon={<Phone size={14}/>} label="Business phone" value={profile.phone}/>
        <ContactRow icon={<Mail size={14}/>} label="Business email" value={profile.email}/>
      </Card>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Who sees this
        </p>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Contact details are shared with a customer only for an active job. They are never
          shown on your public profile or used for browsing.
        </p>
      </Card>
    </div>
  );
}

function ContactRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | null }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "10px 0", borderTop: "1px solid var(--border)" }}>
      <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "var(--text-secondary)" }}>
        {icon} {label}
      </span>
      <span style={{ fontSize: 12.5, color: "var(--text-primary)", fontWeight: 500 }}>{value || "—"}</span>
    </div>
  );
}

/** Verified fields cannot be edited directly; a change goes to ServiceOS for review.
 *  The tenant's verification_status is the only record of that review the backend
 *  keeps -- there is no change-request history table -- so this reports the current
 *  state truthfully instead of listing a history that is not stored. */
function ChangeRequestsTab({ profile }: { profile: BusinessProfileOverview }) {
  const pending = profile.verification_status === "changes_pending_review";
  return (
    <Card style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <ShieldCheck size={16} style={{ color: pending ? "var(--warning-text)" : "var(--success-text)", marginTop: 2 }}/>
        <div>
          <p style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
            {pending ? "A change request is awaiting review" : "No change request pending"}
          </p>
          <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 12px", lineHeight: 1.6 }}>
            {pending
              ? "A change to a verified field has been submitted. Your current details stay live until ServiceOS completes the review."
              : "Verified fields — business name, legal name, registration number, GSTIN and registered address — are locked. Editing one submits a change request for ServiceOS to review."}
          </p>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            Only the current review state is recorded, so past requests are not listed here.
          </p>
        </div>
      </div>
    </Card>
  );
}

/** Profile edits are written to the platform audit log, which the tenant reads through
 *  its own Activity workspace. Pointing there beats a second, partial copy of the same
 *  log that would quietly disagree with it. */
function ActivityTab() {
  return (
    <Card style={{ maxWidth: 760 }}>
      <p style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
        Activity &amp; audit
      </p>
      <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 12px", lineHeight: 1.6 }}>
        Every change to this profile is recorded in your workspace activity log, together with
        who made it and when.
      </p>
      <a href="/activity" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5,
        fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>
        Open Activity <ArrowRight size={13}/>
      </a>
    </Card>
  );
}
