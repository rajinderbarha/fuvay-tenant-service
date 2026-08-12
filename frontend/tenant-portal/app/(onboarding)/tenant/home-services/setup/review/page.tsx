"use client";
/**
 * Tenant Onboarding — Review & Submit (step 8 of 8).
 * Server-side readiness (home_services_setup_service.get_setup_overview) is
 * the sole source of truth for completeness/blockers -- this page only
 * renders it and collects the 3 mandatory declarations before calling the
 * atomic, server-re-validated /setup/submit endpoint.
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2, AlertTriangle, Clock, Info, ChevronDown, ChevronRight, Lock, RefreshCw,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { Card, Btn, Badge, Skeleton, Modal } from "../../../../../../components/shared/ui";
import {
  homeServicesSetupOverviewApi, homeServicesSetupApi, onboardingDeclarationsApi, ServiceOSError,
  type HomeServicesSetupOverview, type HomeServicesSetupSection,
} from "../../../../../../lib/api";

const SECTION_LABELS: Record<string, string> = {
  BUSINESS_PROFILE: "Business profile",
  DOCUMENTS: "Verification documents",
  SERVICES_PRICING: "Services & pricing",
  COVERAGE_AVAILABILITY: "Coverage & availability",
  STAFF_TECHNICIANS: "Staff & technicians",
  FINANCE_READINESS: "Finance readiness",
};

const DECLARATION_TEXT: Record<string, React.ReactNode> = {
  information_accurate: "I confirm the information provided is accurate.",
  authorized_submitter: "I am authorized to submit this business for verification.",
  terms_and_privacy: (
    <>I agree to the <Link href="/legal/terms" target="_blank" style={{ color: "var(--brand)" }}>Terms of Service</Link> and{" "}
      <Link href="/legal/privacy" target="_blank" style={{ color: "var(--brand)" }}>Privacy Notice</Link>.</>
  ),
};

export default function ReviewSubmitPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<HomeServicesSetupOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [publishingServices, setPublishingServices] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    homeServicesSetupOverviewApi.getOverview()
      .then(o => {
        setOverview(o);
        const c: Record<string, boolean> = {};
        for (const item of o.declarations.items) c[item.key] = item.accepted;
        setChecked(c);
      })
      .catch(e => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your setup for review."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  function toggle(key: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  const allChecked = overview ? overview.declarations.items.every(i => checked[i.key]) : false;
  const status = overview?.vertical.status;
  const isLockedForReview = status === "submitted" || status === "under_review";
  const canEditDeclarations = !isLockedForReview;

  async function saveDraft() {
    setSaving(true);
    setError(null);
    try {
      const keys = Object.keys(checked).filter(k => checked[k]);
      if (keys.length) await onboardingDeclarationsApi.accept(keys);
      load();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save your declarations.");
    } finally {
      setSaving(false);
    }
  }

  // Fallback for tenants who reached Review before the Coverage & Availability
  // step started auto-publishing eligible services: publish still-draft,
  // priced services now that coverage necessarily already exists (it's an
  // earlier required step), then re-check readiness.
  async function retryPublishServices() {
    setPublishingServices(true);
    setError(null);
    try {
      const { services } = await homeServicesSetupApi.listEnabled();
      const errors: string[] = [];
      for (const svc of services) {
        if (svc.setup_status === "published") continue;
        try {
          await homeServicesSetupApi.publish(svc.tenant_service_id);
        } catch (err) {
          const name = svc.tenant_display_name ?? "A service";
          errors.push(err instanceof ServiceOSError ? `${name}: ${err.message}` : `${name}: could not be published.`);
        }
      }
      if (errors.length) setError(`Some services still need attention: ${errors.join(" ")}`);
      load();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not publish your services.");
    } finally {
      setPublishingServices(false);
    }
  }

  async function doSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const keys = Object.keys(checked).filter(k => checked[k]);
      if (keys.length) await onboardingDeclarationsApi.accept(keys);
      await homeServicesSetupOverviewApi.submitForReview();
      setConfirmOpen(false);
      router.replace("/tenant/home-services/setup/overview");
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not submit for review. Please try again.");
      setConfirmOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <OnboardingShell activeNav="review">
        <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 16px" }}>Review &amp; submit</h1>
        <Skeleton height={70} style={{ marginBottom: 20 }}/>
        <Skeleton height={420} style={{ marginBottom: 20 }}/>
        <Skeleton height={160}/>
      </OnboardingShell>
    );
  }

  if (error && !overview) {
    return (
      <OnboardingShell activeNav="review">
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your setup for review.
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }
  if (!overview) return null;

  const completedRequired = overview.progress.completed_required;
  const requiredCount = overview.progress.total_required;
  const financeSection = overview.sections.find(s => s.key === "FINANCE_READINESS");
  const depositAmount = (financeSection?.security_deposit_amount as number | undefined) ?? 0;
  const depositDueAfterApproval = !!financeSection?.security_deposit_due_after_approval;

  // sections_ready never depends on declaration-checkbox state, unlike the
  // server's combined can_submit -- allChecked (this page's own local
  // checkbox state) is the up-to-date signal for declarations, so the
  // button enables the moment all 3 are checked instead of staying
  // disabled until an extra, unprompted "Save draft" click.
  const canSubmit = overview.sections_ready && allChecked && !isLockedForReview;

  const readinessBadge = isLockedForReview
    ? { variant: "info" as const, label: "Submitted" }
    : status === "rejected"
    ? { variant: "danger" as const, label: "Rejected" }
    : status === "changes_requested"
    ? { variant: "warning" as const, label: "Changes requested" }
    : overview.blocker_count > 0
    ? { variant: "danger" as const, label: `${overview.blocker_count} blocker${overview.blocker_count === 1 ? "" : "s"}` }
    : { variant: "success" as const, label: "Ready to submit" };

  const applicationReason = status === "rejected" ? overview.vertical.rejection_reason
    : status === "changes_requested" ? overview.vertical.changes_requested_note
    : null;

  return (
    <OnboardingShell activeNav="review">
      <style>{`
        .review-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: start; }
        @media (max-width: 980px) { .review-grid { grid-template-columns: 1fr; } }
        .review-row { border-bottom: 1px solid var(--border); padding: 16px 0; }
        .review-row:last-child { border-bottom: none; }
      `}</style>

      {applicationReason && (
        <div role="alert" style={{
          display: "flex", gap: 10, padding: "14px 16px", borderRadius: 10, marginBottom: 16,
          background: status === "rejected" ? "var(--danger-bg)" : "var(--warning-bg)",
          border: `1px solid ${status === "rejected" ? "var(--danger-border)" : "var(--warning-border)"}`,
        }}>
          <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2, color: status === "rejected" ? "var(--danger-text)" : "var(--warning-text)" }}/>
          <div>
            <p style={{ fontSize: 13.5, fontWeight: 700, margin: "0 0 4px", color: status === "rejected" ? "var(--danger-text)" : "var(--warning-text)" }}>
              {status === "rejected" ? "Your application was rejected" : "Changes requested on your application"}
            </p>
            <p style={{ fontSize: 13, margin: 0, color: status === "rejected" ? "var(--danger-text)" : "var(--warning-text)", lineHeight: 1.5 }}>
              {applicationReason}
            </p>
            <p style={{ fontSize: 12, margin: "6px 0 0", color: "var(--text-secondary)" }}>
              Correct the issue below, then submit again for review.
            </p>
          </div>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Review &amp; submit</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Review your setup before sending it to ServiceOS for verification.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Step 8 of 8</span>
          <Badge variant={readinessBadge.variant} size="lg">
            {readinessBadge.variant === "success" ? <CheckCircle2 size={12}/> : readinessBadge.variant === "danger" ? <AlertTriangle size={12}/> : <Clock size={12}/>}
            {readinessBadge.label}
          </Badge>
        </div>
      </div>

      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, margin: "16px 0" }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
        </div>
      )}

      <div className="review-grid" style={{ marginTop: 20 }}>
        <div style={{ minWidth: 0 }}>
          <Card>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Setup review</p>
            <div>
              {overview.sections.map(s => (
                <SectionRow key={s.key} section={s}
                  expanded={expanded.has(s.key)} onToggle={() => toggle(s.key)}
                  onRetryPublish={s.key === "SERVICES_PRICING" && s.status !== "complete" ? retryPublishServices : undefined}
                  retryingPublish={publishingServices}/>
              ))}
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Declarations</p>
            {overview.declarations.items.map(item => (
              <label key={item.key} style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 12, cursor: canEditDeclarations ? "pointer" : "default", opacity: canEditDeclarations ? 1 : 0.7 }}>
                <input type="checkbox" checked={!!checked[item.key]} disabled={!canEditDeclarations}
                  onChange={e => setChecked({ ...checked, [item.key]: e.target.checked })}
                  style={{ marginTop: 2, width: 16, height: 16, flexShrink: 0 }}/>
                <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>{DECLARATION_TEXT[item.key] ?? item.key}</span>
              </label>
            ))}
            <div style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
              <Lock size={14} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
              <span>Submitting locks this version while it is under review.</span>
            </div>
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Readiness</p>
            <div style={{ textAlign: "center", marginBottom: 10 }}>
              <p style={{ fontSize: 34, fontWeight: 800, color: overview.blocker_count > 0 ? "var(--danger)" : "var(--success)", margin: 0 }}>
                {overview.progress.percentage}%
              </p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{completedRequired} of {requiredCount} sections complete</p>
            </div>
            {overview.blocker_count > 0 && (
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 4px", textAlign: "center" }}>{overview.blocker_count} blocker{overview.blocker_count === 1 ? "" : "s"}</p>
            )}
            {overview.warning_count > 0 && (
              <p style={{ fontSize: 12, color: "var(--warning-text)", margin: 0, textAlign: "center" }}>{overview.warning_count} warning{overview.warning_count === 1 ? "" : "s"}</p>
            )}
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Review process</p>
            {["Submitted", "Admin review", "Changes requested or approved", "Activation requirements", "Go live"].map((label, i) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: i === 4 ? 0 : 14 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", border: "1.5px solid var(--text-tertiary)", flexShrink: 0 }}/>
                <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{label}</span>
              </div>
            ))}
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Submission summary</p>
            <SummaryRow label="Vertical" value="Home Services"/>
            <SummaryRow label="Tenant" value={overview.tenant.name ?? "—"}/>
            <SummaryRow label="Setup status" value={status ?? "—"}/>
            <SummaryRow label="Calc. version" value={overview.progress.calculation_version}/>
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Link href="/tenant/home-services/setup/finance"><Btn variant="secondary">Back</Btn></Link>
        <div style={{ display: "flex", gap: 10 }}>
          <Btn variant="secondary" disabled={saving || isLockedForReview} loading={saving} onClick={saveDraft}>Save draft</Btn>
          <Btn variant="primary" disabled={!canSubmit} onClick={() => setConfirmOpen(true)}>Submit for review</Btn>
        </div>
      </div>

      <Modal open={confirmOpen} onClose={() => !submitting && setConfirmOpen(false)} title="Submit your business for review?">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, margin: "0 0 14px" }}>
          Your current setup will be locked and sent to Super Admin for review. You won&apos;t be able to freely edit
          it while it&apos;s under review. Admin may approve it, reject it, or request changes.
          {depositAmount > 0 && depositDueAfterApproval && " If approved, a security deposit may be required before activation."}
        </p>
        <div style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", marginBottom: 18 }}>
          <Info size={14} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
          <span>Activation requirements, if any, follow after approval.</span>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <Btn variant="secondary" disabled={submitting} onClick={() => setConfirmOpen(false)}>Cancel</Btn>
          <Btn variant="primary" loading={submitting} onClick={doSubmit}>Submit for review</Btn>
        </div>
      </Modal>
    </OnboardingShell>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize" }}>{value}</span>
    </div>
  );
}

function SectionRow({ section, expanded, onToggle, onRetryPublish, retryingPublish }: {
  section: HomeServicesSetupSection; expanded: boolean; onToggle: () => void;
  onRetryPublish?: () => void; retryingPublish?: boolean;
}) {
  const isReviewRow = section.key === "REVIEW_SUBMIT";
  const afterApproval = section.key === "FINANCE_READINESS" && section.security_deposit_due_after_approval;
  const warnings = (section.warnings as { message: string }[] | undefined) ?? [];

  let statusBadge: { variant: "success" | "warning" | "danger" | "muted"; label: string; icon: React.ReactNode };
  if (section.status === "complete") {
    statusBadge = { variant: "success", label: "Complete", icon: <CheckCircle2 size={12}/> };
  } else if (section.status === "locked") {
    statusBadge = { variant: "muted", label: "Locked", icon: <Lock size={12}/> };
  } else if (section.status === "ready") {
    statusBadge = { variant: "success", label: "Ready to submit", icon: <CheckCircle2 size={12}/> };
  } else if (section.status === "optional") {
    statusBadge = { variant: "muted", label: "Optional", icon: <Info size={12}/> };
  } else if (section.blocking_reasons.length > 0) {
    statusBadge = { variant: "danger", label: "Incomplete", icon: <AlertTriangle size={12}/> };
  } else if (isReviewRow) {
    // Every other required section is done (no blocking reasons) and this
    // row itself just hasn't been actioned yet -- it's waiting on the
    // tenant to click Submit, not on any missing setup. Falling through to
    // the generic warning label below wrongly implied something was still
    // wrong here even when the Submit button was already unlocked.
    statusBadge = { variant: "success", label: "Ready to submit", icon: <CheckCircle2 size={12}/> };
  } else {
    statusBadge = { variant: "warning", label: "Needs attention", icon: <AlertTriangle size={12}/> };
  }

  const label = SECTION_LABELS[section.key] ?? section.label;
  const summary = sectionSummary(section);

  return (
    <div className="review-row">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ color: statusBadge.variant === "success" ? "var(--success)" : statusBadge.variant === "danger" ? "var(--danger)" : "var(--text-tertiary)", flexShrink: 0 }}>
          {section.status === "complete" ? <CheckCircle2 size={18}/> : <Info size={18}/>}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{label}</p>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{summary}</p>
        </div>
        <Badge variant={afterApproval ? "warning" : statusBadge.variant} size="sm">
          {afterApproval ? "After approval" : (
            <>{statusBadge.icon}{statusBadge.label}</>
          )}
        </Badge>
        {onRetryPublish && (
          <button onClick={onRetryPublish} disabled={retryingPublish}
            style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", background: "none", border: "1px solid var(--brand)", borderRadius: 6, padding: "4px 10px", cursor: retryingPublish ? "default" : "pointer", opacity: retryingPublish ? 0.6 : 1 }}>
            {retryingPublish ? "Publishing…" : "Publish now"}
          </button>
        )}
        {!isReviewRow && (
          <Link href={sectionEditRoute(section.key)} style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Edit</Link>
        )}
        <button onClick={onToggle} aria-label="Expand" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 4, display: "flex" }}>
          {expanded ? <ChevronDown size={16}/> : <ChevronRight size={16}/>}
        </button>
      </div>
      {expanded && (
        <div style={{ marginTop: 10, paddingLeft: 30, fontSize: 12, color: "var(--text-secondary)" }}>
          {section.blocking_reasons.length > 0 && (
            <ul style={{ margin: "0 0 6px", paddingLeft: 16, color: "var(--danger-text)" }}>
              {section.blocking_reasons.map((b, i) => <li key={i}>{b.message}</li>)}
            </ul>
          )}
          {section.warnings.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 16, color: "var(--warning-text)" }}>
              {section.warnings.map((w, i) => <li key={i}>{w.message}</li>)}
            </ul>
          )}
          {section.blocking_reasons.length === 0 && section.warnings.length === 0 && (
            <p style={{ margin: 0 }}>No outstanding items for this section.</p>
          )}
        </div>
      )}
    </div>
  );
}

function sectionSummary(section: HomeServicesSetupSection): string {
  switch (section.key) {
    case "BUSINESS_PROFILE":
      return "Business identity and registered address";
    case "DOCUMENTS":
      return `${section.uploaded_count ?? 0}/${section.required_count ?? 0} required documents uploaded`;
    case "SERVICES_PRICING":
      return `${section.published_count ?? 0} service(s) configured`;
    case "COVERAGE_AVAILABILITY":
      return `${section.active_areas ?? 0} coverage area(s)`;
    case "STAFF_TECHNICIANS":
      return `${section.active_staff ?? 0} ready technician(s)`;
    case "FINANCE_READINESS":
      return section.security_deposit_amount ? "Security deposit and usage wallet are handled after approval" : "Direct customer payment configured";
    case "REVIEW_SUBMIT":
      return section.status === "complete" ? "Submitted"
        : section.blocking_reasons.length === 0 ? "All required sections are complete — submit below"
        : "Available after required sections are complete";
    default:
      return section.description;
  }
}

function sectionEditRoute(key: string): string {
  const map: Record<string, string> = {
    BUSINESS_PROFILE: "/tenant/home-services/setup/business-profile",
    DOCUMENTS: "/tenant/home-services/setup/documents",
    SERVICES_PRICING: "/tenant/home-services/setup/services-pricing",
    COVERAGE_AVAILABILITY: "/tenant/home-services/setup/coverage-availability",
    STAFF_TECHNICIANS: "/tenant/home-services/setup/staff",
    FINANCE_READINESS: "/tenant/home-services/setup/finance",
  };
  return map[key] ?? "/tenant/home-services/setup/overview";
}
