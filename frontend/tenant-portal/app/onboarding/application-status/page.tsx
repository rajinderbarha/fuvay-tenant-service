"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Clock, CheckCircle2, XCircle, AlertTriangle, RefreshCw, Rocket, UserCog, Mail, ListChecks,
} from "lucide-react";
import { OnboardingShell } from "../../../components/onboarding/OnboardingShell";
import { CorrectionActions } from "../../../components/onboarding/CorrectionActions";
import { Card, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import {
  tenantApplicationStatusApi, ServiceOSError,
  type ApplicationStatus, type ApplicationStatusLifecycleStage,
} from "../../../lib/api";

const STATUS_BADGE: Record<string, { label: string; variant: "success" | "warning" | "danger" | "muted" }> = {
  draft_setup: { label: "Not submitted", variant: "muted" },
  draft: { label: "Not submitted", variant: "muted" },
  submitted: { label: "Submitted", variant: "warning" },
  under_review: { label: "Under review", variant: "warning" },
  changes_requested: { label: "Changes requested", variant: "warning" },
  approved: { label: "Approved", variant: "success" },
  approved_pending_activation: { label: "Approved · Activation pending", variant: "warning" },
  activation_requirements_pending: { label: "Approved · Activation pending", variant: "warning" },
  activating: { label: "Activating", variant: "warning" },
  active: { label: "Active", variant: "success" },
  rejected: { label: "Rejected", variant: "danger" },
  suspended: { label: "Suspended", variant: "danger" },
};

const WHAT_HAPPENS_NEXT: Record<string, { icon: React.ReactNode; text: string }[]> = {
  submitted: [
    { icon: <UserCog size={15}/>, text: "Admin reviews the submitted version" },
    { icon: <Mail size={15}/>, text: "You receive a decision or requested changes" },
    { icon: <ListChecks size={15}/>, text: "Post-approval requirements may follow" },
    { icon: <Rocket size={15}/>, text: "Workspace goes live only after activation" },
  ],
  under_review: [
    { icon: <UserCog size={15}/>, text: "Admin reviews the submitted version" },
    { icon: <Mail size={15}/>, text: "You receive a decision or requested changes" },
    { icon: <ListChecks size={15}/>, text: "Post-approval requirements may follow" },
    { icon: <Rocket size={15}/>, text: "Workspace goes live only after activation" },
  ],
  changes_requested: [
    { icon: <AlertTriangle size={15}/>, text: "Review the requested changes" },
    { icon: <ListChecks size={15}/>, text: "Update the affected setup sections" },
    { icon: <CheckCircle2 size={15}/>, text: "Resolve each request" },
    { icon: <Rocket size={15}/>, text: "Resubmit a new version" },
  ],
  approved: [
    { icon: <CheckCircle2 size={15}/>, text: "Your approval has been recorded" },
    { icon: <Rocket size={15}/>, text: "Your workspace goes live once our team activates it" },
  ],
  approved_pending_activation: [
    { icon: <CheckCircle2 size={15}/>, text: "Your setup has been approved" },
    { icon: <ListChecks size={15}/>, text: "Complete the requirements in the Activation Center" },
    { icon: <Rocket size={15}/>, text: "Your workspace activates automatically once every requirement is met" },
  ],
  activation_requirements_pending: [
    { icon: <CheckCircle2 size={15}/>, text: "Your setup has been approved" },
    { icon: <ListChecks size={15}/>, text: "Complete the requirements in the Activation Center" },
    { icon: <Rocket size={15}/>, text: "Your workspace activates automatically once every requirement is met" },
  ],
  activating: [
    { icon: <Rocket size={15}/>, text: "Your workspace is being activated" },
  ],
  active: [
    { icon: <CheckCircle2 size={15}/>, text: "Customer catalog is published" },
    { icon: <CheckCircle2 size={15}/>, text: "Provider matching is enabled" },
    { icon: <Rocket size={15}/>, text: "Operational workspace is available" },
  ],
  rejected: [
    { icon: <AlertTriangle size={15}/>, text: "Review the decision reason" },
    { icon: <Mail size={15}/>, text: "Contact support if you believe this is in error" },
  ],
};

const ACTIVITY_LABEL: Record<string, string> = {
  "enrollment.submitted": "Setup submitted",
  "enrollment.under_review": "Review started",
  "enrollment.changes_requested": "Changes requested",
  "enrollment.approved": "Approved",
  "enrollment.active": "Activated",
  "enrollment.rejected": "Rejected",
  "enrollment.suspended": "Suspended",
};

function fmt(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleString(undefined, { month: "short", day: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" });
}

const STAGE_TITLES: Record<string, string> = {
  SUBMITTED: "Submitted", ADMIN_REVIEW: "Admin review", DECISION: "Decision",
  ACTIVATION_REQUIREMENTS: "Activation requirements", GO_LIVE: "Go live",
};

function LifecycleTracker({ stages }: { stages: ApplicationStatusLifecycleStage[] }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", overflowX: "auto", padding: "4px 0" }}>
      {stages.map((s, i) => {
        const isLast = i === stages.length - 1;
        const dotColor = s.status === "COMPLETED" ? "var(--success-text)"
          : s.status === "CURRENT" ? "var(--brand)"
          : s.status === "BLOCKED" ? "var(--danger-text)" : "var(--text-tertiary)";
        return (
          <React.Fragment key={s.key}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 96 }}>
              <div style={{
                width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                border: `2px solid ${dotColor}`, color: dotColor,
                background: s.status === "COMPLETED" ? "var(--success-bg)" : "transparent", flexShrink: 0,
              }}>
                {s.status === "COMPLETED" ? <CheckCircle2 size={16}/> : s.status === "CURRENT" ? <Clock size={15}/> : <span style={{ fontSize: 12, fontWeight: 700 }}>{i + 1}</span>}
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginTop: 8, textAlign: "center" }}>{STAGE_TITLES[s.key]}</span>
              <span style={{ fontSize: 11, color: dotColor, marginTop: 2 }}>
                {s.status === "CURRENT" ? "You are here" : s.status === "COMPLETED" ? "Completed"
                  : s.status === "NOT_REQUIRED" ? "Not required" : s.status === "NOT_APPLICABLE" ? "Not applicable"
                  : s.status === "BLOCKED" ? "Action needed" : "Upcoming"}
              </span>
            </div>
            {!isLast && <div style={{ flex: 1, height: 2, background: s.status === "COMPLETED" ? "var(--success-border)" : "var(--border)", marginTop: 15, minWidth: 24 }}/>}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export default function ApplicationStatusPage() {
  const router = useRouter();
  const [data, setData] = useState<ApplicationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    tenantApplicationStatusApi.get()
      .then(d => {
        setData(d);
        if (d.status === "draft_setup" || d.status === "draft") {
          router.replace("/tenant/home-services/setup/overview");
        }
      })
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your application status."))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => { load(); }, [load]);

  // Safe, low-frequency polling; stops on terminal Active/Rejected state.
  useEffect(() => {
    if (!data || data.status === "active" || data.status === "rejected") return;
    const id = window.setInterval(() => { if (document.visibilityState === "visible") load(); }, 30000);
    return () => window.clearInterval(id);
  }, [data, load]);

  if (loading) {
    return (
      <OnboardingShell activeNav="application-status" restricted>
        <Skeleton height={64} style={{ marginBottom: 20 }}/>
        <Skeleton height={220} style={{ marginBottom: 20 }}/>
        <Skeleton height={320}/>
      </OnboardingShell>
    );
  }

  if (error || !data) {
    return (
      <OnboardingShell activeNav="application-status" restricted>
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>We couldn&apos;t load your application status.</p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  const badge = STATUS_BADGE[data.status] ?? { label: data.status_label, variant: "muted" as const };
  const whatNext = WHAT_HAPPENS_NEXT[data.status] ?? [];

  return (
    <OnboardingShell activeNav="application-status" restricted>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--brand)", margin: "0 0 6px" }}>TENANT ONBOARDING</p>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Application status</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>Track your Home Services verification and activation progress.</p>
        </div>
        <Badge variant={badge.variant} size="lg" dot>{badge.label}</Badge>
      </div>

      <CorrectionActions status={data.status}/>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, alignItems: "start" }} className="app-status-grid">
        <style>{`
          @media (max-width: 1024px) { .app-status-grid { grid-template-columns: 1fr !important; } }
        `}</style>

        <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
          <Card>
            <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--warning-bg)", color: "var(--warning-text)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {data.status === "active" ? <CheckCircle2 size={22}/> : data.status === "rejected" ? <XCircle size={22}/> : <Clock size={22}/>}
              </div>
              <div style={{ minWidth: 0 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>{data.status_instruction}</h2>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  {data.submitted_at ? `Submitted on ${fmt(data.submitted_at)}` : ""}
                  {data.submitted_at ? " · " : ""}
                  Submission {data.submission_details.submission_id} · Version {data.submission_details.version}
                </p>
                {data.is_locked && (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "6px 0 0" }}>Your submitted setup is locked while our team reviews it.</p>
                )}
                {data.status === "changes_requested" && data.changes_requested_note && (
                  <div style={{ marginTop: 10, padding: 12, borderRadius: 12, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "var(--warning-text)", margin: 0 }}>{data.changes_requested_note}</p>
                  </div>
                )}
                {data.status === "rejected" && data.rejection_reason && (
                  <div style={{ marginTop: 10, padding: 12, borderRadius: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "var(--danger-text)", margin: 0 }}>{data.rejection_reason}</p>
                  </div>
                )}
              </div>
            </div>
          </Card>

          <Card>
            <LifecycleTracker stages={data.lifecycle}/>
          </Card>

          <Card>
            <h3 id="submitted-setup" style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Submitted setup</h3>
            <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
              {data.snapshot.map((s, i) => (
                <div key={s.key} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px", gap: 10,
                  borderBottom: i < data.snapshot.length - 1 ? "1px solid var(--border)" : "none", flexWrap: "wrap",
                }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{s.label}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Badge variant={s.status === "complete" ? "success" : "muted"} size="sm">
                      {s.status === "complete" ? "Complete" : s.status === "optional" ? "Optional" : "Incomplete"}
                    </Badge>
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Review activity</h3>
            {data.review_activity.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No review activity yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {data.review_activity.map((ev, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                      <CheckCircle2 size={14} style={{ color: "var(--success-text)" }}/>
                      {ACTIVITY_LABEL[ev.action] ?? ev.action}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{fmt(ev.occurred_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
          <Card>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>What happens next</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {whatNext.map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--accent-muted)", color: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{item.icon}</span>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)", paddingTop: 4 }}>{item.text}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Submission details</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Vertical", data.submission_details.vertical],
                ["Submission ID", data.submission_details.submission_id],
                ["Version", String(data.submission_details.version)],
                ["Submitted by", data.submission_details.submitted_by ?? "—"],
              ].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <span style={{ color: "var(--text-tertiary)" }}>{k}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </div>
          </Card>

          {["approved", "approved_pending_activation", "activation_requirements_pending", "activating", "active"].includes(data.status) && (
            <Card>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Activation</h3>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 8 }}>
                <span style={{ color: "var(--text-tertiary)" }}>Usage credits</span>
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>Optional until the booking floor</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ color: "var(--text-tertiary)" }}>Technician seats</span>
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>Purchase before adding technicians</span>
              </div>
            </Card>
          )}

          <Card>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>Need help?</h3>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 14px" }}>Our support team is here if you have any questions about your submission.</p>
            <Btn variant="secondary" fullWidth onClick={() => router.push("/help")}>Contact support</Btn>
          </Card>
        </div>
      </div>

      <div style={{ marginTop: 24, display: "flex", gap: 10, flexWrap: "wrap" }}>
        {data.available_actions.includes("CONTINUE_CORRECTIONS") && (
          <Btn variant="primary" onClick={() => router.push("/tenant/home-services/setup/overview")}>Continue corrections</Btn>
        )}
        {data.available_actions.includes("GO_TO_WORKSPACE") && (
          <Btn variant="primary" icon={<Rocket size={14}/>} onClick={() => router.push("/dashboard")}>Go to workspace</Btn>
        )}
        {data.available_actions.includes("VIEW_ACTIVATION_CENTER") && (
          <Btn variant="primary" icon={<Rocket size={14}/>} onClick={() => router.push("/onboarding/activation-center")}>Go to Activation Center</Btn>
        )}
        {data.available_actions.includes("VIEW_SUBMITTED_SETUP") && (
          <Btn variant="secondary" onClick={() => router.push("/tenant/home-services/setup/overview")}>View submitted setup</Btn>
        )}
      </div>
    </OnboardingShell>
  );
}
