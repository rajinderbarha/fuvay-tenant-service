"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, RefreshCw, Hourglass, XCircle, AlertTriangle } from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { CorrectionActions } from "../../../../../../components/onboarding/CorrectionActions";
import { VerticalLifecycleBar } from "../../../../../../components/onboarding/VerticalLifecycleBar";
import {
  SetupProgressCard, WorkspaceStatusCard, OnboardingNextSteps,
  OnboardingHelpCard, OnboardingPolicyBanner, AutosaveStatus,
} from "../../../../../../components/onboarding/SetupOverviewCards";
import { Card, Badge, Skeleton, Btn } from "../../../../../../components/shared/ui";
import { PageHeader, PageShell } from "@serviceos/design-system";
import { homeServicesSetupOverviewApi, ServiceOSError, type HomeServicesSetupOverview } from "../../../../../../lib/api";

const EYEBROW_BY_STATUS: Record<string, string> = {
  draft_setup: "WORKSPACE CREATED",
  draft: "SETUP IN PROGRESS",
  changes_requested: "CHANGES REQUESTED",
  submitted: "UNDER REVIEW",
  under_review: "UNDER REVIEW",
  approved: "ACTIVATION PENDING",
  rejected: "REJECTED",
  suspended: "SUSPENDED",
};

const STATUS_LABEL: Record<string, string> = {
  draft_setup: "Setup not submitted",
  draft: "Setup not submitted",
  changes_requested: "Changes requested",
  submitted: "Under review",
  under_review: "Under review",
  approved: "Approved — activation pending",
  active: "Active",
  rejected: "Rejected",
  suspended: "Suspended",
};

// Destinations this page renders in place -- everything else means the
// tenant does not belong on this onboarding page and must be redirected
// (e.g. an activated tenant must land on the real Tenant Dashboard, never
// stay stuck on onboarding -- see spec: "ACTIVE: Redirect... do not continue
// showing onboarding as the primary landing page").
const ONBOARDING_DESTINATIONS = new Set(["HOME_SERVICES_SETUP_OVERVIEW", "HOME_SERVICES_CHANGES_REQUESTED"]);
const EXTERNAL_DESTINATION_ROUTES: Record<string, string> = {
  TENANT_DASHBOARD: "/dashboard",
  RESTRICTED_WORKSPACE: "/dashboard",
  RESUME_SIGNUP: "/register",
  VERIFY_CONTACT: "/register",
  SELECT_VERTICAL: "/register",
  STAFF_PORTAL: "/dashboard",
  HOME_SERVICES_UNDER_REVIEW: "/onboarding/application-status",
  HOME_SERVICES_ACTIVATION: "/onboarding/activation-center",
};

export default function HomeServicesSetupOverviewPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<HomeServicesSetupOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    homeServicesSetupOverviewApi.getRouting()
      .then(routing => {
        if (!ONBOARDING_DESTINATIONS.has(routing.next_destination)) {
          setRedirecting(true);
          router.replace(EXTERNAL_DESTINATION_ROUTES[routing.next_destination] ?? "/dashboard");
          return;
        }
        return homeServicesSetupOverviewApi.getOverview().then(setOverview);
      })
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your setup progress."))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => { load(); }, [load]);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await homeServicesSetupOverviewApi.submitForReview();
      load();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not submit for review.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || redirecting) {
    return (
      <OnboardingShell activeNav="overview">
        <PageShell>
          <PageHeader title="Setup overview" description="Track your Home Services setup and prepare your workspace for review." />
          <Skeleton height={140}/><Skeleton height={120}/><Skeleton height={320}/>
        </PageShell>
      </OnboardingShell>
    );
  }

  if (error || !overview) {
    return (
      <OnboardingShell activeNav="overview">
        <PageShell>
          <PageHeader title="Setup overview" description="Track your Home Services setup and prepare your workspace for review." />
          <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your setup progress.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
          </Card>
        </PageShell>
      </OnboardingShell>
    );
  }

  const status = overview.vertical.status;
  const eyebrow = EYEBROW_BY_STATUS[status] ?? "SETUP IN PROGRESS";
  const reviewSection = overview.sections.find(s => s.key === "REVIEW_SUBMIT");
  const canSubmit = !!reviewSection && !reviewSection.locked && (status === "draft_setup" || status === "draft" || status === "changes_requested");

  const isRejected = status === "rejected";
  const isSuspended = status === "suspended";
  const iconColorVars = isRejected
    ? { bg: "var(--danger-bg)", border: "var(--danger-border)", text: "var(--danger-text)" }
    : isSuspended
    ? { bg: "var(--warning-bg)", border: "var(--warning-border)", text: "var(--warning-text)" }
    : { bg: "var(--success-bg)", border: "var(--success-border)", text: "var(--success-text)" };
  const HeaderIcon = isRejected ? XCircle : isSuspended ? AlertTriangle : CheckCircle2;

  const description = isRejected
    ? (overview.vertical.rejection_reason
        ? `Your Home Services setup was rejected: ${overview.vertical.rejection_reason}`
        : "Your Home Services setup was rejected. Contact support if you believe this decision should be reviewed.")
    : isSuspended
    ? (overview.vertical.suspend_reason
        ? `Home Services is suspended: ${overview.vertical.suspend_reason}`
        : "Home Services is currently suspended. Contact support for details.")
    : status === "changes_requested" && overview.vertical.changes_requested_note
    ? `Changes requested: ${overview.vertical.changes_requested_note}`
    : "Your business workspace is ready. Complete Home Services setup to prepare for admin review.";

  return (
    <OnboardingShell activeNav="overview">
      <PageShell>
      <PageHeader title="Setup overview" description="Track your Home Services setup and prepare your workspace for review." />
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div style={{
            width: 48, height: 48, borderRadius: "50%", background: iconColorVars.bg,
            border: `1px solid ${iconColorVars.border}`, display: "flex", alignItems: "center",
            justifyContent: "center", color: iconColorVars.text, flexShrink: 0,
          }}>
            <HeaderIcon size={24}/>
          </div>
          <div style={{ flex: 1, minWidth: 240 }}>
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: iconColorVars.text, margin: "0 0 4px" }}>{eyebrow}</p>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
              Welcome to Fuvay{overview.tenant.name ? `, ${overview.tenant.name}` : ""}
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "6px 0 0" }}>
              {description}
            </p>
          </div>
          <Badge variant={status === "active" ? "success" : status === "changes_requested" ? "warning" : (isRejected || isSuspended) ? "danger" : "muted"} size="lg">
            {(status === "draft_setup" || status === "draft") && <Hourglass size={11}/>}
            {STATUS_LABEL[status] ?? status}
          </Badge>
        </div>
      </Card>

      <VerticalLifecycleBar stages={overview.lifecycle.stages}/>
      <CorrectionActions status={status}/>

      <style>{`
        .hs-setup-overview-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: start; }
        @media (max-width: 900px) { .hs-setup-overview-grid { grid-template-columns: 1fr; } }
      `}</style>
      <div className="hs-setup-overview-grid">
        <div style={{ minWidth: 0 }}>
          <SetupProgressCard overview={overview}/>
          {canSubmit && (
            <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
              <Btn variant="primary" loading={submitting} onClick={handleSubmit}>Submit for review</Btn>
            </div>
          )}
        </div>
        <div style={{ minWidth: 0 }}>
          <WorkspaceStatusCard overview={overview}/>
          <OnboardingNextSteps status={status}/>
          <OnboardingHelpCard/>
        </div>
      </div>

      <OnboardingPolicyBanner/>
      <div style={{ marginTop: 12 }}><AutosaveStatus state="saved"/></div>
      </PageShell>
    </OnboardingShell>
  );
}
