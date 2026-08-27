"use client";
import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Home, Circle, Lock, AlertCircle, ChevronRight,
  BookOpen, Headphones, Loader2, IdCard, FileText, Tag, MapPin, Users2, Wallet, ClipboardCheck,
} from "lucide-react";
import { Card, Badge, Btn } from "../shared/ui";
import type { HomeServicesSetupOverview, HomeServicesSetupSection } from "../../lib/api";

const NEXT_ACTION_ROUTES: Record<string, string> = {
  EDIT_BUSINESS_PROFILE: "/tenant/home-services/setup/business-profile",
  EDIT_DOCUMENTS: "/tenant/home-services/setup/documents",
  EDIT_SERVICES_PRICING: "/tenant/home-services/setup/services-pricing",
  EDIT_COVERAGE_AVAILABILITY: "/tenant/home-services/setup/coverage-availability",
  EDIT_STAFF: "/tenant/home-services/setup/staff",
  EDIT_FINANCE: "/tenant/home-services/setup/finance",
  REVIEW_AND_SUBMIT: "/tenant/home-services/setup/review",
};

const SECTION_ROUTES: Record<string, string> = {
  BUSINESS_PROFILE: "/tenant/home-services/setup/business-profile",
  DOCUMENTS: "/tenant/home-services/setup/documents",
  SERVICES_PRICING: "/tenant/home-services/setup/services-pricing",
  COVERAGE_AVAILABILITY: "/tenant/home-services/setup/coverage-availability",
  STAFF_TECHNICIANS: "/tenant/home-services/setup/staff",
  FINANCE_READINESS: "/tenant/home-services/setup/finance",
  REVIEW_SUBMIT: "/tenant/home-services/setup/review",
};

const SECTION_ICONS: Record<string, React.ReactNode> = {
  BUSINESS_PROFILE: <IdCard size={17}/>,
  DOCUMENTS: <FileText size={17}/>,
  SERVICES_PRICING: <Tag size={17}/>,
  COVERAGE_AVAILABILITY: <MapPin size={17}/>,
  STAFF_TECHNICIANS: <Users2 size={17}/>,
  FINANCE_READINESS: <Wallet size={17}/>,
  REVIEW_SUBMIT: <ClipboardCheck size={17}/>,
};

function statusMeta(s: HomeServicesSetupSection) {
  if (s.status === "complete") return { label: "Complete", variant: "success" as const };
  if (s.status === "ready") return { label: "Ready", variant: "success" as const };
  if (s.status === "locked") return { label: "Locked", variant: "muted" as const };
  if (s.status === "optional") return { label: "Optional for now", variant: "info" as const };
  if (s.status === "blocked") return { label: "Needs attention", variant: "danger" as const };
  if (s.key === "REVIEW_SUBMIT" && s.locked) return { label: "Locked", variant: "muted" as const };
  return { label: "Not started", variant: "muted" as const };
}

/** One continuous card -- progress header + checklist rows, matching the
 * single-panel "Home Services setup" layout (not two separate cards). */
const LOCKED_VERTICAL_STATUSES = new Set(["submitted", "under_review", "approved", "active"]);

export function SetupProgressCard({ overview }: { overview: HomeServicesSetupOverview }) {
  const router = useRouter();
  const { progress, next_action, sections } = overview;
  const nextRoute = NEXT_ACTION_ROUTES[next_action.key] ?? "/tenant/home-services/setup/overview";
  const readOnly = LOCKED_VERTICAL_STATUSES.has(overview.vertical.status);
  return (
    <Card padding={0} style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap", padding: "20px 20px 4px" }}>
        <div style={{
          width: 48, height: 48, borderRadius: "50%", background: "var(--accent-muted)",
          display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", flexShrink: 0,
          border: "1px solid var(--accent)",
        }}>
          <Home size={22}/>
        </div>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Home Services setup</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "8px 0" }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: "var(--brand)" }}>{progress.percentage}% complete</span>
            <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              {progress.completed_required} of {progress.total_required} sections ready
            </span>
          </div>
          <div role="progressbar" aria-label="Home Services setup progress" aria-valuenow={progress.percentage} aria-valuemin={0} aria-valuemax={100}
            style={{ height: 8, background: "var(--surface-sunken)", borderRadius: 999, overflow: "hidden", border: "1px solid var(--border)" }}>
            <div style={{
              height: "100%", width: `${progress.percentage}%`, borderRadius: 999,
              background: progress.percentage === 100 ? "var(--success)" : "var(--brand)",
              transition: "width 0.6s ease",
            }}/>
          </div>
        </div>
        {!readOnly && (
          <div className="hs-continue-setup-wrap" style={{ alignSelf: "center" }}>
            <Btn variant="primary" icon={<ChevronRight size={15}/>} onClick={() => router.push(nextRoute)}>Continue setup</Btn>
          </div>
        )}
      </div>
      <style>{`
        @media (max-width: 640px) {
          .hs-continue-setup-wrap { width: 100%; align-self: stretch !important; }
          .hs-continue-setup-wrap button { width: 100%; }
        }
      `}</style>

      {readOnly && (
        <div style={{
          margin: "0 20px 16px", padding: "10px 14px", borderRadius: "var(--radius-md)",
          background: "var(--info-bg)", border: "1px solid var(--info-border)",
        }}>
          <p style={{ fontSize: 12.5, color: "var(--info-text)", margin: 0 }}>
            Your setup sections are locked while Home Services is {overview.vertical.status.replace(/_/g, " ")}.
          </p>
        </div>
      )}

      <div style={{ height: 1, background: "var(--border)", margin: "16px 0 0" }}/>

      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {sections.map((s, i) => {
          const meta = statusMeta(s);
          const rowLocked = readOnly || (s.key === "REVIEW_SUBMIT" && !!s.locked);
          const href = SECTION_ROUTES[s.key];
          const content = (
            <div style={{
              display: "flex", alignItems: "center", gap: 14, padding: "16px 20px",
              borderBottom: i < sections.length - 1 ? "1px solid var(--border)" : "none",
              minHeight: 44, opacity: rowLocked ? 0.7 : 1,
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%", background: "var(--accent-muted)",
                display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", flexShrink: 0,
                border: "1px solid var(--accent)",
              }}>
                {SECTION_ICONS[s.key] ?? <Circle size={17}/>}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 14, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>{s.label}</p>
                <p style={{ fontSize: 12, margin: "2px 0 0", color: "var(--text-tertiary)" }}>{s.description}</p>
              </div>
              <Badge variant={meta.variant}>{meta.label}</Badge>
              {rowLocked
                ? <Lock size={16} aria-label="Locked" style={{ color: "var(--text-tertiary)" }}/>
                : <ChevronRight size={16} style={{ color: "var(--text-tertiary)" }}/>}
            </div>
          );
          return (
            <li key={s.key}>
              {rowLocked || !href
                ? <div aria-disabled="true" title={readOnly ? "Locked while your submission is under admin review" : rowLocked ? "Complete required sections first" : undefined}>{content}</div>
                : <Link href={href} style={{ textDecoration: "none", display: "block" }}>{content}</Link>}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

const VERTICAL_STATUS_LABEL: Record<string, string> = {
  draft_setup: "Setup not submitted",
  draft: "Setup not submitted",
  changes_requested: "Changes requested",
  submitted: "Under review",
  under_review: "Under review",
  approved: "Approved",
  active: "Active",
  rejected: "Rejected",
  suspended: "Suspended",
};

export function WorkspaceStatusCard({ overview }: { overview: HomeServicesSetupOverview }) {
  const w = overview.workspace_status;
  const row = (label: string, variant: "success" | "warning" | "danger" | "muted", text: string) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0" }}>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
      <Badge variant={variant}>{text}</Badge>
    </div>
  );
  const verticalStatus = overview.vertical.status;
  const verticalVariant = verticalStatus === "active" ? "success"
    : (verticalStatus === "rejected" || verticalStatus === "suspended") ? "danger"
    : "warning"; // draft_setup/draft/changes_requested/submitted/under_review/approved all read as "not yet active"
  return (
    <Card style={{ marginBottom: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Workspace status</h3>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {row("Owner account", w.owner_account_verified ? "success" : "warning", w.owner_account_verified ? "Verified" : "Pending")}
        {row("Business profile", w.business_profile_status === "complete" ? "success" : "warning", w.business_profile_status === "complete" ? "Complete" : "In progress")}
        {row("Home Services", verticalVariant, VERTICAL_STATUS_LABEL[verticalStatus] ?? verticalStatus.replace(/_/g, " "))}
        {row("Admin review", w.admin_review_status !== "not_submitted" ? "success" : "muted",
             w.admin_review_status === "not_submitted" ? "Not submitted" : "Submitted")}
      </div>
    </Card>
  );
}

const DEFAULT_STEPS = ["Complete required setup", "Submit Home Services for review", "Resolve changes if requested", "Activate after approval"];
const CHANGES_REQUESTED_STEPS = ["Review requested changes", "Correct affected sections", "Resubmit", "Continue admin review"];

export function OnboardingNextSteps({ status }: { status: string }) {
  const steps = status === "changes_requested" ? CHANGES_REQUESTED_STEPS : DEFAULT_STEPS;
  const currentIndex = status === "submitted" || status === "under_review" ? 1
    : status === "changes_requested" ? 0
    : status === "approved" ? 3 : 0;
  return (
    <Card style={{ marginBottom: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>What happens next?</h3>
      <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
        {steps.map((step, i) => (
          <li key={step} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{
              width: 22, height: 22, borderRadius: "50%", flexShrink: 0, display: "flex",
              alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700,
              background: i === currentIndex ? "var(--brand)" : "var(--surface-sunken)",
              color: i === currentIndex ? "var(--text-on-brand)" : "var(--text-tertiary)",
              border: i === currentIndex ? "none" : "1px solid var(--border)",
            }}>{i + 1}</span>
            <span style={{ fontSize: 13, color: i === currentIndex ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: i === currentIndex ? 600 : 400 }}>{step}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function OnboardingHelpCard() {
  const router = useRouter();
  return (
    <Card>
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>Need help getting started?</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <Btn variant="secondary" fullWidth icon={<BookOpen size={14}/>} onClick={() => router.push("/tenant/home-services/setup/overview")}>View setup guide</Btn>
        <Btn variant="secondary" fullWidth icon={<Headphones size={14}/>} onClick={() => router.push("/help")}>Contact support</Btn>
      </div>
    </Card>
  );
}

export function OnboardingPolicyBanner() {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, padding: "14px 18px", marginTop: 20,
      background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: "var(--radius-lg)",
    }}>
      <AlertCircle size={16} style={{ color: "var(--info-text)", flexShrink: 0 }}/>
      <p style={{ fontSize: 13, color: "var(--info-text)", margin: 0 }}>
        No package or payment is required during signup. Service pricing remains fully controlled by your business.
        A top-up plan is required after admin approval — it grants the usage credits you spend on jobs and the technician seats you need to receive bookings.
      </p>
    </div>
  );
}

export function AutosaveStatus({ state }: { state: "idle" | "saving" | "saved" | "failed" }) {
  if (state === "idle") return null;
  if (state === "saving") return (
    <p style={{ fontSize: 12, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 6 }}>
      <Loader2 size={12} style={{ animation: "spin 0.7s linear infinite" }}/> Saving…
    </p>
  );
  if (state === "failed") return <p style={{ fontSize: 12, color: "var(--danger-text)" }}>Save failed — Retry</p>;
  return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Your progress saves automatically.</p>;
}
