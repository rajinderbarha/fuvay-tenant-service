"use client";
import React, { useCallback, useMemo } from "react";
import Link from "next/link";
import { RefreshCw, ClipboardList, Wrench } from "lucide-react";
import {
  myStatusApi, authApi, isTenantOwnerRole,
  type ProviderStatusResult, type OfferingBookableStatus, type EnabledOffering,
  type PackageAssignmentSummary, type TenantSecurityDepositStatus, type TenantCreditWalletDetail,
  type ProviderServiceArea, type ProviderTeamMember, type ProviderAvailabilityRule,
} from "../../../../lib/api";
import { trustBadgesApi } from "../../../../lib/api";
import { TrustBadges } from "../../../../components/TrustBadges";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import { blockerMeta, safeNum, safeArray, type RequiredAction } from "../../../../lib/status-format";
import { getTenantSetupChecklist } from "../../../../lib/api-foundation/tenant-modules";
import { TenantStatusHero } from "../../../../components/status/TenantStatusHero";
import { TenantStatusActionCenter } from "../../../../components/status/TenantStatusActionCenter";
import { TenantReadinessScoreCards, type ScoreCard } from "../../../../components/status/TenantReadinessScoreCards";
import { TenantStatusSectionError } from "../../../../components/status/TenantStatusBadge";
import {
  TenantOfferingBookabilityPanel, TenantSetupStatusChecklist, type ChecklistItem,
  TenantFinanceReadinessPanel, TenantOperationalReadinessPanel,
  TenantVisibilityRulesPanel, TenantStatusActivityTimeline, type ActivityRow,
} from "../../../../components/status/TenantStatusPanels";

export default function ProviderStatusPage() {
  const tenant = useTenant();

  const meApi             = useApi(useCallback(() => authApi.me(), []));
  const statusApi         = useApi(useCallback(() => getTenantSetupChecklist(), []));
  const offeringStatusApi = useApi(useCallback(() => myStatusApi.getOfferingStatuses(), []));
  const enabledOfferingsApi = useApi(useCallback(() => myStatusApi.getEnabledOfferings(), []));
  const packageApi        = useApi(useCallback(() => myStatusApi.getPackageSummary(), []));
  const depositApi        = useApi(useCallback(() => myStatusApi.getSecurityDeposit(), []));
  const walletApi         = useApi(useCallback(() => myStatusApi.getCreditWallet(), []));
  const areasApi          = useApi(useCallback(() => myStatusApi.getServiceAreas(), []));
  const teamApi           = useApi(useCallback(() => myStatusApi.getTeamMembers(), []));
  const availabilityApi   = useApi(useCallback(() => myStatusApi.getAvailability(), []));
  const activityApi       = useApi(useCallback(() => myStatusApi.getAuditLog(15), []));
  const badgesApi         = useApi(useCallback(() => trustBadgesApi.myBadges(), []));

  const refreshAll = useCallback(() => {
    statusApi.refetch(); offeringStatusApi.refetch(); enabledOfferingsApi.refetch();
    packageApi.refetch(); depositApi.refetch(); walletApi.refetch();
    areasApi.refetch(); teamApi.refetch(); availabilityApi.refetch(); activityApi.refetch();
  }, [statusApi, offeringStatusApi, enabledOfferingsApi, packageApi, depositApi, walletApi, areasApi, teamApi, availabilityApi, activityApi]);

  const refreshAction = useAction(useCallback(() => myStatusApi.refreshStatus(), []), { onSuccess: refreshAll });

  const isTenantOwner = isTenantOwnerRole(meApi.data?.role);
  // FINAL-L5 fix: permission-aware recalculate, not just a silently-disabled
  // button (a disabled button with no explanation hides the capability
  // rather than communicating why it's unavailable).
  const canRecalculate = isTenantOwner;

  const s: ProviderStatusResult | null = statusApi.data ?? null;
  const offeringStatuses: OfferingBookableStatus[] = safeArray(offeringStatusApi.data?.statuses);
  const enabledOfferings: EnabledOffering[] = safeArray(enabledOfferingsApi.data?.offerings);
  const pkg: PackageAssignmentSummary | null = packageApi.data ?? null;
  const deposit: TenantSecurityDepositStatus | null = depositApi.data ?? null;
  const wallet: TenantCreditWalletDetail | null = walletApi.data ?? null;
  const areas: ProviderServiceArea[] = safeArray(areasApi.data?.areas);
  const team: ProviderTeamMember[] = safeArray(teamApi.data?.members);
  const activeTeam = team.filter(m => m.status === "active");
  const availability: ProviderAvailabilityRule[] = safeArray(availabilityApi.data?.rules);
  const activityLogs = safeArray(activityApi.data?.logs);

  const requiredActions: RequiredAction[] = useMemo(() => {
    const actions: RequiredAction[] = [];
    const push = (code: string, reason: string) => {
      const m = blockerMeta(code);
      actions.push({ code, severity: m.severity, title: m.title, reason, cta: m.cta, route: m.route, ruleKey: m.ruleKey });
    };
    if (pkg && !pkg.has_package) push("package_inactive", "No package selected yet.");
    else if (pkg && pkg.status !== "active") push("package_inactive", pkg.message || "Your package is not active.");
    if (wallet && safeNum(wallet.balance) <= 0) push("usage_credits_missing", `Your usage credit balance is 0. Usage credits are required to accept and complete jobs.`);
    if (deposit && deposit.status !== "paid" && deposit.status !== "refunded")
      push("security_deposit_pending", `Your ₹${safeNum(deposit.required_amount).toLocaleString("en-IN")} security deposit is pending. This can prevent customer bookings.`);
    if (areas.length === 0) push("service_area_missing", "You have not configured any service areas yet.");
    if (enabledOfferings.length === 0) push("service_missing", "You have not enabled any service offerings yet.");
    if (activeTeam.length === 0) push("active_technician_missing", "You do not have any active technicians assigned.");
    if (availability.length === 0) push("availability_missing", "You have not configured your working hours yet.");
    if (!tenant.tenantName) push("business_profile_incomplete", "Add your business name, GST, and address.");
    for (const b of [...safeArray(s?.visibility_blockers), ...safeArray(s?.bookability_blockers)]) {
      if (!actions.some(a => a.code === b.code)) {
        const m = blockerMeta(b.code);
        actions.push({ code: b.code, severity: m.severity, title: m.title, reason: b.message, cta: m.cta, route: b.route || m.route, ruleKey: m.ruleKey });
      }
    }
    return actions;
  }, [pkg, wallet, deposit, areas.length, enabledOfferings.length, activeTeam.length, availability.length, tenant.tenantName, s]);

  const totalChecks = 8;
  const blockedChecks = requiredActions.length;
  const pct = Math.round(((totalChecks - Math.min(blockedChecks, totalChecks)) / totalChecks) * 100);

  const bookableCount = enabledOfferings.filter(o =>
    offeringStatuses.find(os => os.provider_enabled_offering_id === o.provider_enabled_offering_id)?.is_bookable
  ).length;

  const financeReady = deposit?.status === "paid" && safeNum(wallet?.balance) > 0 && pkg?.status === "active";
  const opsReady = activeTeam.length > 0 && availability.length > 0;
  const serviceSetupReady = !!tenant.tenantName && areas.length > 0 && enabledOfferings.length > 0;

  // ── Setup Readiness Checklist (backend-computed, real data only) ──────────
  const checklistItems: ChecklistItem[] = [
    { key: "package_active", label: "Package Active", ruleKey: "package_active",
      status: pkg?.status === "active" ? "completed" : "blocked",
      reason: pkg?.message || (pkg?.status === "active" ? "Your package is active." : "No active package."),
      cta: "View Package", ctaRoute: "/finance/package" },
    { key: "usage_credits", label: "Usage Credits Available", ruleKey: "usage_credits_available",
      status: safeNum(wallet?.balance) > 0 ? "completed" : "blocked",
      reason: `Balance: ${safeNum(wallet?.balance).toLocaleString("en-IN")} credits`,
      cta: "View Usage Credit Ledger", ctaRoute: "/finance/usage-credit-ledger" },
    { key: "deposit", label: "Security Deposit Received/Waived", ruleKey: "security_deposit_received_or_waived",
      status: deposit?.status === "paid" || deposit?.status === "refunded" ? "completed" : "blocked",
      reason: deposit ? `₹${safeNum(deposit.required_amount).toLocaleString("en-IN")} deposit ${deposit.status === "paid" ? "paid" : "pending"}` : "Loading…",
      cta: "View Security Deposit", ctaRoute: "/finance/security-deposit" },
    { key: "service_area", label: "At Least One Service Area", ruleKey: "service_area_active",
      status: areas.length > 0 ? "completed" : "blocked",
      reason: `${areas.length} service area(s) configured.`,
      cta: "Add Service Area", ctaRoute: "/provider/service-areas" },
    { key: "offering", label: "At Least One Service Offering", ruleKey: "offering_active",
      status: enabledOfferings.length > 0 ? "completed" : "blocked",
      reason: `${enabledOfferings.length} offering(s) enabled.`,
      cta: "Enable an Offering", ctaRoute: "/provider/offerings" },
    { key: "technician", label: "At Least One Active Technician", ruleKey: "active_technician_present",
      status: activeTeam.length > 0 ? "completed" : "blocked",
      reason: `${activeTeam.length} active technician(s).`,
      cta: "Add Technician", ctaRoute: "/provider/staff" },
    { key: "availability", label: "Availability Configured", ruleKey: "availability_configured",
      status: availability.length > 0 ? "completed" : "blocked",
      reason: `${availability.length} availability rule(s) configured.`,
      cta: "Set Availability", ctaRoute: "/provider/availability" },
    { key: "business_profile", label: "Business Profile Complete", ruleKey: "business_profile_complete",
      status: tenant.tenantName ? "completed" : "blocked",
      reason: tenant.tenantName ? "Business name configured." : "Add business details, logo, and contacts.",
      cta: "Complete Business Profile", ctaRoute: "/profile" },
  ];

  // ── Readiness score cards (6, per acceptance spec) ─────────────────────────
  const scoreCards: ScoreCard[] = [
    { id: "overall", label: "Overall Readiness", value: `${pct}%`,
      variant: pct === 100 ? "success" : pct >= 50 ? "warning" : "danger",
      reason: `${blockedChecks} of ${totalChecks} checks blocked` },
    { id: "visibility", label: "Customer Visibility", value: s?.is_visible ? "Visible" : "Hidden",
      variant: s?.is_visible ? "success" : "danger",
      reason: s?.is_visible ? "Your profile appears in customer search." : "Complete setup to become visible." },
    { id: "bookability", label: "Offerings Bookability",
      value: enabledOfferings.length === 0 ? "No offerings" : `${bookableCount} / ${enabledOfferings.length} bookable`,
      variant: enabledOfferings.length === 0 ? "info" : bookableCount === enabledOfferings.length ? "success" : "warning",
      reason: enabledOfferings.length === 0 ? "Enable your first service offering." : "Add coverage and service areas to unlock bookings.",
      ctaLabel: "Manage Offerings", ctaRoute: "/provider/offerings" },
    { id: "finance", label: "Finance Readiness", value: financeReady ? "Ready" : "Blocked",
      variant: financeReady ? "success" : "danger",
      reason: deposit?.status !== "paid" ? "Security deposit pending" : safeNum(wallet?.balance) <= 0 ? "No usage credits" : "Package not active",
      ctaLabel: "View Finance", ctaRoute: "/finance/package" },
    { id: "service_setup", label: "Service Setup", value: serviceSetupReady ? "Ready" : "Incomplete",
      variant: serviceSetupReady ? "success" : "warning",
      reason: serviceSetupReady ? "Business profile, area, and offering are configured." : "Complete your business profile, service area, and offering.",
      ctaLabel: "View Setup Checklist", ctaRoute: "/provider/status" },
    { id: "operations", label: "Operations Readiness",
      value: `${activeTeam.length} technician${activeTeam.length !== 1 ? "s" : ""} ready`,
      variant: opsReady ? "success" : "warning",
      reason: opsReady ? "Operations look ready." : "Add staff or configure availability.",
      ctaLabel: "View Operations", ctaRoute: "/provider/staff" },
  ];

  // ── Operational readiness rows (real data only) ─────────────────────────────
  const operationalRows = [
    { label: "Service Areas",        count: `${areas.length} / 5 configured`,            status: areas.length > 0 ? "ready" : "missing",             blockingReason: null, ctaLabel: "Manage", ctaRoute: "/provider/service-areas" },
    { label: "Services / Offerings", count: `${enabledOfferings.length} enabled`,        status: enabledOfferings.length > 0 ? "ready" : "missing",  blockingReason: null, ctaLabel: "Manage", ctaRoute: "/provider/offerings" },
    { label: "Active Technicians",   count: `${activeTeam.length} / ${Math.max(team.length, 1)} active`, status: activeTeam.length > 0 ? "ready" : "missing", blockingReason: null, ctaLabel: "Manage", ctaRoute: "/provider/staff" },
    { label: "Availability",         count: `${availability.length} rule(s) configured`, status: availability.length > 0 ? "ready" : "missing",      blockingReason: null, ctaLabel: "Manage", ctaRoute: "/tenant/setup/availability" },
    { label: "Documents",            count: "Not independently tracked yet",             status: "warning",                                          blockingReason: null, ctaLabel: "Manage", ctaRoute: "/documents" },
    { label: "Pricing",              count: enabledOfferings.length > 0 ? "Configured per offering" : "Configure after enabling offerings",
      status: enabledOfferings.length > 0 ? "ready" : "warning", blockingReason: null, ctaLabel: "Manage", ctaRoute: "/provider/pricing" },
  ];

  // ── Activity rows (real audit log, request-id preserved) ───────────────────
  const activityRows: ActivityRow[] = activityLogs.map((l: unknown) => {
    const log = l as Record<string, unknown>;
    return {
      event: String(log.action_type ?? log.event ?? "—"),
      result: "—",
      actor: String(log.actor_role ?? log.actor ?? "system"),
      requestId: log.request_id ? String(log.request_id) : null,
      createdAt: String(log.created_at ?? ""),
    };
  });

  const primaryBlockingReason = requiredActions.length > 0 ? requiredActions[0].reason : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, minHeight: "100%" }}>
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 6 }}>
        <Link href="/dashboard" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Dashboard</Link>
        <span>›</span>
        <span>Provider Visibility & Bookability</span>
      </div>

      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, letterSpacing: "-0.01em" }}>Provider Visibility & Bookability</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>Track whether your business is visible to customers and ready to receive bookings.</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={refreshAll} disabled={refreshAction.loading} style={{
            display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 13px", borderRadius: 8, fontSize: 13,
            fontWeight: 500, cursor: "pointer", border: "1px solid var(--border)", background: "transparent", color: "var(--text-primary)" }}>
            <RefreshCw size={13}/> Refresh Status
          </button>
          {canRecalculate ? (
            <button onClick={() => refreshAction.execute()} disabled={refreshAction.loading} style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 13px", borderRadius: 8, fontSize: 13,
              fontWeight: 500, cursor: "pointer", border: "none", background: "var(--brand)", color: "#fff" }}>
              <RefreshCw size={13}/> {refreshAction.loading ? "Recalculating…" : "Recalculate Readiness"}
            </button>
          ) : (
            <span title="Permission required: only the tenant owner can recalculate readiness." style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 13px", borderRadius: 8, fontSize: 13,
              fontWeight: 500, border: "1px solid var(--border)", color: "var(--text-tertiary)" }}>
              <RefreshCw size={13}/> Recalculate Readiness — Permission required
            </span>
          )}
          <Link href="/provider/status"><button style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 13px",
            borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", border: "1px solid var(--border)", background: "transparent" }}>
            <ClipboardList size={13}/> View Setup Checklist
          </button></Link>
          <Link href="/provider/offerings"><button style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 13px",
            borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", border: "1px solid var(--border)", background: "transparent" }}>
            <Wrench size={13}/> Manage Offerings
          </button></Link>
        </div>
      </div>

      {refreshAction.error && (
        <p style={{ fontSize: 12, color: "var(--danger-text, #b91c1c)" }}>
          {refreshAction.error} {refreshAction.requestId && `(Request ID: ${refreshAction.requestId})`}
        </p>
      )}

      {/* Hero */}
      {statusApi.error && !statusApi.loading ? (
        <TenantStatusSectionError title="Status Failed to Load" message={statusApi.error}
          requestId={statusApi.requestId} section="statusApi" onRetry={() => statusApi.refetch()}/>
      ) : (
        <TenantStatusHero
          tenantName={tenant.tenantName || "Your Business"}
          vertical={tenant.vertical}
          isVisible={!!s?.is_visible}
          isBookable={!!s?.is_bookable}
          setupCompletionPct={pct}
          lastEvaluatedAt={s?.last_evaluated_at ?? null}
          primaryBlockingReason={primaryBlockingReason}
          onFixRequiredActions={() => window.scrollTo({ top: 400, behavior: "smooth" })}
        />
      )}

      {/* Required Actions */}
      <TenantStatusActionCenter actions={requiredActions} lastCheckedAt={s?.last_evaluated_at ?? null}/>

      {/* Score Cards */}
      <TenantReadinessScoreCards cards={scoreCards}/>

      {/* Trust Badges — what customers see on your profile */}
      <div style={{ background: "var(--surface, #fff)", border: "1px solid var(--border, #e5e5e5)",
        borderRadius: 14, padding: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Trust Badges</h2>
          <span style={{ fontSize: 12, color: "var(--text-tertiary, #888)" }}>
            Earned automatically — shown to customers on your profile
          </span>
        </div>
        <TrustBadges badges={badgesApi.data ?? []}
          empty="No badges earned yet. Keep your ratings high and jobs completed to earn them." />
      </div>

      {/* Offerings Status */}
      {(enabledOfferingsApi.error || offeringStatusApi.error) ? (
        <TenantStatusSectionError title="Offerings Failed to Load" message={enabledOfferingsApi.error || offeringStatusApi.error || ""}
          requestId={enabledOfferingsApi.requestId || offeringStatusApi.requestId}
          section="enabledOfferingsApi/offeringStatusApi"
          onRetry={() => { enabledOfferingsApi.refetch(); offeringStatusApi.refetch(); }}/>
      ) : (
        <TenantOfferingBookabilityPanel offerings={enabledOfferings} statuses={offeringStatuses} loading={enabledOfferingsApi.loading}/>
      )}

      {/* Setup Readiness Checklist */}
      <TenantSetupStatusChecklist items={checklistItems} lastCheckedAt={s?.last_evaluated_at ?? null}/>

      {/* Finance + Operational */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {(packageApi.error || depositApi.error || walletApi.error) ? (
          <TenantStatusSectionError title="Finance Data Failed to Load" message={packageApi.error || depositApi.error || walletApi.error || ""}
            requestId={packageApi.requestId || depositApi.requestId || walletApi.requestId}
            section="packageApi/depositApi/walletApi"
            onRetry={() => { packageApi.refetch(); depositApi.refetch(); walletApi.refetch(); }}/>
        ) : (
          <TenantFinanceReadinessPanel
            packageName={pkg?.package_name ?? ""}
            packageStatus={pkg?.status ?? ""}
            packageMessage={pkg?.message ?? ""}
            creditBalance={safeNum(wallet?.balance)}
            includedCredits={safeNum(pkg?.included_credits)}
            depositRequired={safeNum(deposit?.required_amount)}
            depositPaid={safeNum(deposit?.paid_amount)}
            depositStatus={deposit?.status ?? ""}
            financeReady={!!financeReady}
          />
        )}

        {(teamApi.error || availabilityApi.error || areasApi.error) ? (
          <TenantStatusSectionError title="Operations Data Failed to Load" message={teamApi.error || availabilityApi.error || areasApi.error || ""}
            requestId={teamApi.requestId || availabilityApi.requestId || areasApi.requestId}
            section="teamApi/availabilityApi/areasApi"
            onRetry={() => { teamApi.refetch(); availabilityApi.refetch(); areasApi.refetch(); }}/>
        ) : (
          <TenantOperationalReadinessPanel rows={operationalRows}/>
        )}
      </div>

      {/* How bookability is calculated */}
      <TenantVisibilityRulesPanel/>

      {/* Recent Status Activity */}
      <TenantStatusActivityTimeline rows={activityRows} loading={activityApi.loading}/>
    </div>
  );
}
