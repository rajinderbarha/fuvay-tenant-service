"use client";
import React, { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import {
  RefreshCw, ClipboardList, Wrench, Building2, Eye, Shield, Users2,
  CheckCircle2, XCircle, AlertTriangle, ChevronRight, Info, ChevronDown,
  Activity, Gauge, Calendar, AlertCircle, Copy,
} from "lucide-react";
import {
  myStatusApi, authApi,
  type ProviderStatusResult, type OfferingBookableStatus, type EnabledOffering,
  type PackageAssignmentSummary, type TenantSecurityDepositStatus, type TenantCreditWalletDetail,
  type ProviderServiceArea, type ProviderTeamMember, type ProviderAvailabilityRule,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import { blockerMeta, safeNum, safeArray } from "../../../../lib/status-format";
import { ApiErrorState, ApiLoadingState } from "../../../../components/shared/ApiStates";
import { getTenantSetupChecklist } from "../../../../lib/api-foundation/tenant-modules";

// ── tiny helpers ─────────────────────────────────────────────────────────────
function safeDate(v: unknown): string {
  if (!v) return "—";
  try { return new Date(String(v)).toLocaleString("en-IN", { day:"numeric", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit" }); }
  catch { return String(v); }
}
function GreenPill({ label, icon }: { label: string; icon?: React.ReactNode }) {
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, padding:"5px 12px", borderRadius:999,
      background:"rgba(34,197,94,0.15)", border:"1px solid rgba(34,197,94,0.3)", color:"#22c55e",
      fontSize:13, fontWeight:600 }}>
      {icon}{label}
    </span>
  );
}
function RedPill({ label }: { label: string }) {
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, padding:"5px 12px", borderRadius:999,
      background:"rgba(239,68,68,0.15)", border:"1px solid rgba(239,68,68,0.3)", color:"#ef4444",
      fontSize:13, fontWeight:600 }}>
      {label}
    </span>
  );
}
function WarnPill({ label }: { label: string }) {
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, padding:"5px 12px", borderRadius:999,
      background:"rgba(245,158,11,0.15)", border:"1px solid rgba(245,158,11,0.3)", color:"#f59e0b",
      fontSize:13, fontWeight:600 }}>
      {label}
    </span>
  );
}

// ── types ─────────────────────────────────────────────────────────────────────
interface RequiredAction {
  code: string; severity: string; title: string; reason: string;
  cta?: string; route?: string; ruleKey?: string;
}

export default function ProviderStatusPage() {
  const tenant = useTenant();
  const [howOpen, setHowOpen] = useState(false);

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

  const refreshAll = useCallback(() => {
    statusApi.refetch(); offeringStatusApi.refetch(); enabledOfferingsApi.refetch();
    packageApi.refetch(); depositApi.refetch(); walletApi.refetch();
    areasApi.refetch(); teamApi.refetch(); availabilityApi.refetch(); activityApi.refetch();
  }, [statusApi, offeringStatusApi, enabledOfferingsApi, packageApi, depositApi, walletApi, areasApi, teamApi, availabilityApi, activityApi]);

  const refreshAction = useAction(useCallback(() => myStatusApi.refreshStatus(), []), { onSuccess: refreshAll });

  const isTenantOwner = meApi.data?.role === "tenant_owner" || meApi.data?.role === undefined;

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
    for (const b of [...safeArray(s?.visibility_blockers), ...safeArray(s?.bookability_blockers)]) {
      if (!actions.some(a => a.code === b.code)) {
        const m = blockerMeta(b.code);
        actions.push({ code: b.code, severity: m.severity, title: m.title, reason: b.message, cta: m.cta, route: b.route || m.route, ruleKey: m.ruleKey });
      }
    }
    return actions;
  }, [pkg, wallet, deposit, areas.length, enabledOfferings.length, activeTeam.length, availability.length, s]);

  const totalChecks = 7;
  const blockedChecks = requiredActions.length;
  const pct = Math.round(((totalChecks - Math.min(blockedChecks, totalChecks)) / totalChecks) * 100);

  const bookableCount = enabledOfferings.filter(o =>
    offeringStatuses.find(os => os.provider_enabled_offering_id === o.provider_enabled_offering_id)?.is_bookable
  ).length;

  const financeReady = deposit?.status === "paid" && safeNum(wallet?.balance) > 0 && pkg?.status === "active";
  const opsReady = activeTeam.length > 0 && availability.length > 0;
  const overallStatus = (s?.is_visible && s?.is_bookable) ? "Visible & Bookable"
    : s?.is_visible ? "Visible (Not Bookable)"
    : s?.is_bookable ? "Bookable (Not Visible)"
    : "Not Ready";
  const isFullyReady = s?.is_visible && s?.is_bookable;

  const C = {
    bg:      "var(--surface-sunken, #080e18)",
    card:    "var(--surface, #0d1520)",
    border:  "var(--border, rgba(255,255,255,0.08))",
    text:    "var(--text-primary, #f1f5f9)",
    sub:     "var(--text-secondary, rgba(255,255,255,0.55))",
    ter:     "var(--text-tertiary, rgba(255,255,255,0.35))",
    brand:   "var(--brand, #3b82f6)",
    green:   "#22c55e",
    red:     "#ef4444",
    amber:   "#f59e0b",
  };

  const btn = (variant: "primary"|"secondary", onClick?: ()=>void, disabled?: boolean, loading?: boolean) => ({
    display:"inline-flex" as const, alignItems:"center" as const, gap:6,
    padding:"8px 14px", borderRadius:8, fontSize:13, fontWeight:500,
    cursor: disabled ? "not-allowed" : "pointer",
    fontFamily:"inherit", border:"none", outline:"none",
    opacity: disabled ? 0.55 : 1, transition:"opacity 0.15s",
    background: variant === "primary" ? C.brand : "transparent",
    color: variant === "primary" ? "#fff" : C.text,
    ...(variant === "secondary" ? { border:`1px solid ${C.border}` } : {}),
  });

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20, minHeight:"100%", color:C.text }}>
      <style>{`
        .sp-card{background:${C.card};border:1px solid ${C.border};border-radius:14px}
        .sp-row-sep+.sp-row-sep{border-top:1px solid ${C.border}}
        .sp-link{color:${C.brand};font-size:13px;font-weight:500;text-decoration:none;display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
        .sp-link:hover{opacity:0.8}
        .sp-tbl{width:100%;border-collapse:collapse}
        .sp-tbl th{font-size:12px;font-weight:600;color:${C.ter};text-transform:uppercase;letter-spacing:0.05em;padding:10px 16px;text-align:left;border-bottom:1px solid ${C.border}}
        .sp-tbl td{font-size:13px;color:${C.text};padding:12px 16px;border-bottom:1px solid ${C.border}}
        .sp-tbl tr:last-child td{border-bottom:none}
        .sp-btn-sec{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;border:1px solid ${C.border};background:transparent;color:${C.text};white-space:nowrap}
        .sp-btn-sec:hover{border-color:rgba(255,255,255,0.2)}
        .sp-btn-pri{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;border:none;background:${C.brand};color:#fff;white-space:nowrap}
        .sp-btn-pri:hover{opacity:0.9}
        .chk-ok{color:${C.green}}
        .chk-err{color:${C.red}}
        .chk-warn{color:${C.amber}}
        @keyframes spin{to{transform:rotate(360deg)}}
        .spinning{animation:spin 1s linear infinite}
      `}</style>

      {/* ── Breadcrumb ── */}
      <div style={{ fontSize:12, color:C.ter, display:"flex", alignItems:"center", gap:6 }}>
        <Link href="/dashboard" style={{ color:C.ter, textDecoration:"none" }}>Dashboard</Link>
        <ChevronRight size={12}/>
        <span>Provider Visibility &amp; Bookability</span>
      </div>

      {/* ── Page Header ── */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 style={{ fontSize:24, fontWeight:800, margin:0, letterSpacing:"-0.01em" }}>Provider Visibility &amp; Bookability</h1>
          <p style={{ fontSize:13, color:C.sub, margin:"4px 0 0" }}>Track whether your business is visible to customers and ready to receive bookings.</p>
        </div>
        <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
          <button className="sp-btn-sec" onClick={refreshAll} disabled={refreshAction.loading}>
            <RefreshCw size={13} className={refreshAction.loading ? "spinning" : ""}/> Refresh Status
          </button>
          {isTenantOwner ? (
            <button className="sp-btn-pri" onClick={()=>refreshAction.execute()} disabled={refreshAction.loading}>
              <RefreshCw size={13} className={refreshAction.loading ? "spinning" : ""}/>
              {refreshAction.loading ? "Recalculating…" : "Recalculate Readiness"}
            </button>
          ) : (
            <button className="sp-btn-sec" disabled><RefreshCw size={13}/> Recalculate Readiness</button>
          )}
          <Link href="/provider/status"><button className="sp-btn-sec"><ClipboardList size={13}/> View Setup Checklist</button></Link>
          <Link href="/provider/offerings"><button className="sp-btn-sec"><Wrench size={13}/> Manage Offerings</button></Link>
        </div>
      </div>

      {/* ── Error state (FRONTEND-CONNECT-01: statusApi failed) ── */}
      {statusApi.error && !statusApi.loading && (
        <ApiErrorState
          error={{ code: "STATUS_LOAD_FAILED", message: statusApi.error, request_id: statusApi.requestId ?? undefined }}
          onRetry={refreshAll}
        />
      )}

      {/* ── Loading state (first paint, no cached data yet) ── */}
      {statusApi.loading && !s && <ApiLoadingState rows={4}/>}

      {/* ── Hero Card ── */}
      <div className="sp-card" style={{ padding:"20px 24px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"auto 1fr auto auto", gap:24, alignItems:"center", flexWrap:"wrap" }}>

          {/* Business identity */}
          <div style={{ display:"flex", alignItems:"center", gap:14 }}>
            <div style={{ width:52, height:52, borderRadius:12, background:"rgba(59,130,246,0.15)",
              border:"1px solid rgba(59,130,246,0.25)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <Building2 size={24} style={{ color:C.brand }}/>
            </div>
            <div>
              <p style={{ fontSize:16, fontWeight:700, margin:0 }}>{tenant.tenantName || "Your Business"}</p>
              <p style={{ fontSize:12, color:C.sub, margin:"2px 0 0" }}>{tenant.vertical || "Home Services"}</p>
            </div>
          </div>

          {/* Overall status */}
          <div style={{ borderLeft:`1px solid ${C.border}`, paddingLeft:24 }}>
            <p style={{ fontSize:12, color:C.ter, margin:"0 0 4px", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Overall Status</p>
            <p style={{ fontSize:22, fontWeight:800, margin:0, color: isFullyReady ? C.green : s?.is_visible ? C.amber : C.red }}>
              {statusApi.loading ? "Loading…" : overallStatus}
            </p>
          </div>

          {/* Setup completion */}
          <div style={{ borderLeft:`1px solid ${C.border}`, paddingLeft:24, minWidth:220 }}>
            <p style={{ fontSize:12, color:C.ter, margin:"0 0 4px", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Setup Completion</p>
            <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:6 }}>
              <span style={{ fontSize:24, fontWeight:800 }}>{pct}%</span>
              <div style={{ flex:1, height:6, background:"rgba(255,255,255,0.1)", borderRadius:99, overflow:"hidden" }}>
                <div style={{ width:`${pct}%`, height:"100%", borderRadius:99,
                  background: pct === 100 ? C.green : pct >= 50 ? C.brand : C.amber,
                  transition:"width 0.4s ease" }}/>
              </div>
            </div>
            <p style={{ fontSize:11, color:C.ter, margin:0 }}>Last recalculated: {safeDate(s?.last_evaluated_at)}</p>
          </div>

          {/* Visibility + Bookability badges */}
          <div style={{ borderLeft:`1px solid ${C.border}`, paddingLeft:24, display:"flex", flexDirection:"column", gap:12 }}>
            <div>
              <p style={{ fontSize:11, color:C.ter, margin:"0 0 5px", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Customer Visibility</p>
              {s?.is_visible
                ? <GreenPill label="Visible" icon={<Eye size={13}/>}/>
                : <RedPill label="Hidden"/>}
            </div>
            <div>
              <p style={{ fontSize:11, color:C.ter, margin:"0 0 5px", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>Bookable Status</p>
              {s?.is_bookable
                ? <GreenPill label="Bookable" icon={<Calendar size={13}/>}/>
                : <RedPill label="Not Bookable"/>}
            </div>
          </div>
        </div>
      </div>

      {/* ── Action Required ── */}
      {requiredActions.length > 0 && (
        <div className="sp-card" style={{ padding:"20px 24px" }}>
          <div style={{ display:"grid", gridTemplateColumns:"200px 1fr", gap:24 }}>
            <div>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
                <AlertTriangle size={16} style={{ color:C.amber }}/>
                <p style={{ fontSize:14, fontWeight:700, margin:0 }}>Action Required</p>
              </div>
              <p style={{ fontSize:12, color:C.sub, margin:0, lineHeight:1.5 }}>Resolve the following issues to become fully bookable.</p>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
              {requiredActions.slice(0, 4).map((a, i) => (
                <div key={a.code} style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:12,
                  padding:"12px 0", borderTop: i > 0 ? `1px solid ${C.border}` : "none" }}>
                  <div style={{ display:"flex", alignItems:"flex-start", gap:10 }}>
                    <XCircle size={16} style={{ color:C.red, flexShrink:0, marginTop:1 }}/>
                    <div>
                      <p style={{ fontSize:13, fontWeight:600, margin:"0 0 2px" }}>{a.title}</p>
                      <p style={{ fontSize:12, color:C.sub, margin:0 }}>{a.reason}</p>
                    </div>
                  </div>
                  {a.route && (
                    <Link href={a.route} className="sp-link" style={{ flexShrink:0 }}>
                      {a.cta ?? "Fix Now"} <ChevronRight size={13}/>
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── 5 Score Cards ── */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12 }}>
        {/* Overall Readiness */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
            <p style={{ fontSize:12, color:C.ter, margin:0, fontWeight:500 }}>Overall Readiness</p>
            <Gauge size={16} style={{ color:C.sub }}/>
          </div>
          <p style={{ fontSize:28, fontWeight:800, margin:"0 0 4px",
            color: pct === 100 ? C.green : pct >= 50 ? C.amber : C.red }}>{pct}%</p>
          <p style={{ fontSize:11, color:C.sub, margin:0 }}>{blockedChecks} of {totalChecks} checks blocked</p>
        </div>

        {/* Customer Visibility */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
            <p style={{ fontSize:12, color:C.ter, margin:0, fontWeight:500 }}>Customer Visibility</p>
            <Eye size={16} style={{ color: s?.is_visible ? C.green : C.sub }}/>
          </div>
          <p style={{ fontSize:22, fontWeight:800, margin:"0 0 4px",
            color: s?.is_visible ? C.green : C.red }}>{s?.is_visible ? "Visible" : "Hidden"}</p>
          <p style={{ fontSize:11, color:C.sub, margin:0 }}>{s?.is_visible ? "Your profile appears in customer search." : "Complete setup to become visible."}</p>
        </div>

        {/* Offerings Bookability */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
            <p style={{ fontSize:12, color:C.ter, margin:0, fontWeight:500 }}>Offerings Bookability</p>
            <Calendar size={16} style={{ color:C.sub }}/>
          </div>
          <p style={{ fontSize:22, fontWeight:800, margin:"0 0 4px" }}>
            {enabledOfferings.length === 0 ? <span style={{ color:C.sub, fontSize:14 }}>No offerings enabled yet</span>
              : <span style={{ color: bookableCount === enabledOfferings.length ? C.green : C.amber }}>{bookableCount} / {enabledOfferings.length} bookable</span>}
          </p>
          <p style={{ fontSize:11, color:C.sub, margin:0 }}>
            {enabledOfferings.length === 0 ? "Enable your first service offering." : "Add coverage and service areas to unlock bookings."}
          </p>
        </div>

        {/* Finance Readiness */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
            <p style={{ fontSize:12, color:C.ter, margin:0, fontWeight:500 }}>Finance Readiness</p>
            <Shield size={16} style={{ color: financeReady ? C.green : C.red }}/>
          </div>
          <p style={{ fontSize:22, fontWeight:800, margin:"0 0 4px", color: financeReady ? C.green : C.red }}>
            {financeReady ? "Ready" : "Blocked"}
          </p>
          <p style={{ fontSize:11, color:C.sub, margin:"0 0 8px" }}>
            {deposit?.status !== "paid" ? "Security deposit pending" : safeNum(wallet?.balance) <= 0 ? "No usage credits" : "Package not active"}
          </p>
          <Link href="/finance/package" className="sp-link">View Finance <ChevronRight size={12}/></Link>
        </div>

        {/* Operations Readiness */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
            <p style={{ fontSize:12, color:C.ter, margin:0, fontWeight:500 }}>Operations Readiness</p>
            <Users2 size={16} style={{ color: opsReady ? C.green : C.sub }}/>
          </div>
          <p style={{ fontSize:20, fontWeight:800, margin:"0 0 4px", color: opsReady ? C.green : C.amber }}>
            {activeTeam.length} technician{activeTeam.length !== 1 ? "s" : ""} ready
          </p>
          <p style={{ fontSize:11, color:C.sub, margin:"0 0 8px" }}>
            {opsReady ? "Operations look ready." : "Add staff or configure availability."}
          </p>
          <Link href="/provider/staff" className="sp-link">View Operations <ChevronRight size={12}/></Link>
        </div>
      </div>

      {/* ── Offerings Status ── */}
      <div className="sp-card">
        <div style={{ padding:"18px 20px 14px", borderBottom:`1px solid ${C.border}` }}>
          <p style={{ fontSize:15, fontWeight:700, margin:"0 0 2px" }}>Offerings Status</p>
          <p style={{ fontSize:12, color:C.sub, margin:0 }}>Review the bookability status of your service offerings.</p>
        </div>
        {enabledOfferingsApi.loading ? (
          <div style={{ padding:20, color:C.ter, fontSize:13 }}>Loading offerings…</div>
        ) : enabledOfferings.length === 0 ? (
          <div style={{ padding:"24px 20px", textAlign:"center", color:C.ter, fontSize:13 }}>
            No offerings enabled yet. <Link href="/provider/offerings" className="sp-link">Enable an offering</Link>
          </div>
        ) : (
          <table className="sp-tbl">
            <thead>
              <tr>
                <th>Offering</th><th>Type Coverage</th><th>Brand Coverage</th>
                <th>Bookable Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {enabledOfferings.map(o => {
                const os = offeringStatuses.find(s => s.provider_enabled_offering_id === o.provider_enabled_offering_id);
                const isBookable = os?.is_bookable ?? false;
                return (
                  <tr key={o.provider_enabled_offering_id}>
                    <td style={{ fontWeight:600 }}>{o.offering_name ?? "Service"}</td>
                    <td style={{ color:C.sub }}>
                      {(os as unknown as Record<string,unknown>)?.type_coverage ? "Configured" : "Not configured"}
                    </td>
                    <td style={{ color:C.sub }}>
                      {(os as unknown as Record<string,unknown>)?.brand_coverage ? "Configured" : "Not configured"}
                    </td>
                    <td>{isBookable ? <GreenPill label="Bookable"/> : <RedPill label="Blocked"/>}</td>
                    <td>
                      <Link href={`/provider/offerings/${o.provider_enabled_offering_id}`} className="sp-link">
                        View Offering <ChevronRight size={12}/>
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Setup Readiness Checklist ── */}
      <div className="sp-card">
        <div style={{ padding:"18px 20px 14px", borderBottom:`1px solid ${C.border}` }}>
          <p style={{ fontSize:15, fontWeight:700, margin:"0 0 2px" }}>Setup Readiness Checklist</p>
          <p style={{ fontSize:12, color:C.sub, margin:0 }}>Complete the required setup items to unlock full bookability.</p>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:0 }}>
          {/* Business & Setup */}
          <div style={{ padding:"16px 20px", borderRight:`1px solid ${C.border}` }}>
            <p style={{ fontSize:12, fontWeight:700, color:C.sub, margin:"0 0 12px", textTransform:"uppercase", letterSpacing:"0.05em" }}>Business &amp; Setup</p>
            {[
              { label:"Package Active", done: pkg?.status === "active", note: pkg?.message || (pkg?.status === "active" ? "Your package is active." : "No active package.") },
              { label:"Business Profile Complete", done: !!tenant.tenantName, note: tenant.tenantName ? "Business name configured." : "Add business details, logo, and contacts." },
              { label:"At Least One Service Area", done: areas.length > 0, note: `${areas.length} service area(s) configured.` },
            ].map(item => (
              <div key={item.label} style={{ display:"flex", gap:10, marginBottom:12 }}>
                {item.done
                  ? <CheckCircle2 size={16} className="chk-ok" style={{ flexShrink:0, marginTop:1 }}/>
                  : <XCircle size={16} className="chk-err" style={{ flexShrink:0, marginTop:1 }}/>}
                <div>
                  <p style={{ fontSize:13, fontWeight:600, margin:"0 0 1px" }}>{item.label}</p>
                  <p style={{ fontSize:11, color:C.sub, margin:0 }}>{item.note}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Finance & Credits */}
          <div style={{ padding:"16px 20px", borderRight:`1px solid ${C.border}` }}>
            <p style={{ fontSize:12, fontWeight:700, color:C.sub, margin:"0 0 12px", textTransform:"uppercase", letterSpacing:"0.05em" }}>Finance &amp; Credits</p>
            {[
              { label:"Usage Credits Available", done: safeNum(wallet?.balance) > 0, note: `Balance: ${safeNum(wallet?.balance).toLocaleString("en-IN")} credits` },
              { label:"Security Deposit Received/Waived", done: deposit?.status === "paid" || deposit?.status === "refunded",
                note: deposit ? `₹${safeNum(deposit.required_amount).toLocaleString("en-IN")} deposit ${deposit.status === "paid" ? "paid" : "pending"}` : "Loading…" },
            ].map(item => (
              <div key={item.label} style={{ display:"flex", gap:10, marginBottom:12 }}>
                {item.done
                  ? <CheckCircle2 size={16} className="chk-ok" style={{ flexShrink:0, marginTop:1 }}/>
                  : <XCircle size={16} className="chk-err" style={{ flexShrink:0, marginTop:1 }}/>}
                <div>
                  <p style={{ fontSize:13, fontWeight:600, margin:"0 0 1px" }}>{item.label}</p>
                  <p style={{ fontSize:11, color:C.sub, margin:0 }}>{item.note}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Operations */}
          <div style={{ padding:"16px 20px" }}>
            <p style={{ fontSize:12, fontWeight:700, color:C.sub, margin:"0 0 12px", textTransform:"uppercase", letterSpacing:"0.05em" }}>Operations</p>
            {[
              { label:"At Least One Service Offering", done: enabledOfferings.length > 0, note: `${enabledOfferings.length} offering(s) enabled.` },
              { label:"At Least One Active Technician", done: activeTeam.length > 0, note: `${activeTeam.length} active technician(s).` },
              { label:"Availability Configured", done: availability.length > 0, note: `${availability.length} availability rule(s) configured.` },
            ].map(item => (
              <div key={item.label} style={{ display:"flex", gap:10, marginBottom:12 }}>
                {item.done
                  ? <CheckCircle2 size={16} className="chk-ok" style={{ flexShrink:0, marginTop:1 }}/>
                  : <XCircle size={16} className="chk-err" style={{ flexShrink:0, marginTop:1 }}/>}
                <div>
                  <p style={{ fontSize:13, fontWeight:600, margin:"0 0 1px" }}>{item.label}</p>
                  <p style={{ fontSize:11, color:C.sub, margin:0 }}>{item.note}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Finance + Operational (2-col) ── */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>

        {/* Finance Readiness */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
            <p style={{ fontSize:15, fontWeight:700, margin:0 }}>Finance Readiness</p>
            {financeReady ? <GreenPill label="Ready"/> : <RedPill label="Blocked"/>}
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              {[
                { label:"Package Status", value: pkg?.status === "active" ? "Active" : (pkg?.status ?? "None"),
                  color: pkg?.status === "active" ? C.green : C.amber, dot:true },
                { label:"Usage Credit Balance", value: `${safeNum(wallet?.balance).toLocaleString("en-IN")} credits`,
                  color: safeNum(wallet?.balance) > 0 ? C.text : C.red, dot:false },
                { label:"Security Deposit", value: deposit ? `₹${safeNum(deposit.required_amount).toLocaleString("en-IN")} — ${deposit.status === "paid" ? "Paid" : "Pending"}` : "—",
                  color: deposit?.status === "paid" ? C.text : C.red, dot:false },
              ].map(row => (
                <div key={row.label} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                  padding:"10px 0", borderBottom:`1px solid ${C.border}` }}>
                  <span style={{ fontSize:13, color:C.sub }}>{row.label}</span>
                  <span style={{ fontSize:13, fontWeight:600, color:row.color, display:"flex", alignItems:"center", gap:6 }}>
                    {row.dot && <span style={{ width:7, height:7, borderRadius:"50%", background:row.color, display:"inline-block" }}/>}
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
            <div style={{ padding:"14px 16px", background:"rgba(255,255,255,0.03)", borderRadius:10, border:`1px solid ${C.border}` }}>
              <p style={{ fontSize:12, fontWeight:700, color:C.sub, margin:"0 0 6px" }}>Completed Job Deduction</p>
              <p style={{ fontSize:12, color:C.ter, margin:0, lineHeight:1.6 }}>
                Usage credits are deducted from your balance after each completed job, per the pricing configured for that service. This happens at job completion, not during setup.
              </p>
            </div>
          </div>
        </div>

        {/* Operational Readiness */}
        <div className="sp-card" style={{ padding:"18px 20px" }}>
          <p style={{ fontSize:15, fontWeight:700, margin:"0 0 14px" }}>Operational Readiness</p>
          <table className="sp-tbl" style={{ marginTop:0 }}>
            <tbody>
              {[
                { label:"Service Areas",       count:`${areas.length} / 5 configured`,           status: areas.length > 0 ? "ready" : "missing",             route:"/provider/service-areas" },
                { label:"Services / Offerings", count:`${enabledOfferings.length} enabled`,       status: enabledOfferings.length > 0 ? "ready" : "missing",  route:"/provider/offerings" },
                { label:"Active Technicians",   count:`${activeTeam.length} / ${Math.max(team.length,1)} active`, status: activeTeam.length > 0 ? "ready" : "missing", route:"/provider/staff" },
                { label:"Availability",         count:`${availability.length} rule(s) configured`, status: availability.length > 0 ? "ready" : "missing",     route:"/tenant/setup/availability" },
                { label:"Documents",            count:"Not independently tracked yet",            status:"warning",                                            route:"/documents" },
                { label:"Pricing",              count: enabledOfferings.length > 0 ? "Configured per offering" : "Configure after enabling offerings",
                  status: enabledOfferings.length > 0 ? "ready" : "warning",                                                                                  route:"/provider/pricing" },
              ].map(row => (
                <tr key={row.label}>
                  <td style={{ paddingLeft:0, fontWeight:500, fontSize:13 }}>{row.label}</td>
                  <td style={{ color:C.sub, fontSize:12 }}>{row.count}</td>
                  <td>
                    {row.status === "ready"   ? <GreenPill label="Ready"/>
                    : row.status === "missing" ? <RedPill label="Missing"/>
                    : <WarnPill label="Warning"/>}
                  </td>
                  <td style={{ paddingRight:0, textAlign:"right" }}>
                    <Link href={row.route} className="sp-link">Manage</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── How bookability is calculated ── */}
      <div className="sp-card">
        <button
          onClick={() => setHowOpen(v => !v)}
          style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"16px 20px", background:"none", border:"none", cursor:"pointer", color:C.text, fontFamily:"inherit" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <Info size={15} style={{ color:C.brand }}/>
            <span style={{ fontSize:14, fontWeight:600 }}>How bookability is calculated</span>
          </div>
          <ChevronDown size={15} style={{ color:C.ter, transform: howOpen ? "rotate(180deg)" : "none", transition:"transform 0.2s" }}/>
        </button>
        {howOpen && (
          <div style={{ padding:"0 20px 18px", fontSize:13, color:C.sub, lineHeight:1.7 }}>
            Your business becomes bookable when approval, package, usage credits, security deposit, service areas, offerings, coverage, active technicians, pricing, availability, and required documents satisfy platform rules.
          </div>
        )}
      </div>

      {/* ── Recent Status Activity ── */}
      <div className="sp-card">
        <div style={{ padding:"18px 20px 14px", borderBottom:`1px solid ${C.border}` }}>
          <p style={{ fontSize:15, fontWeight:700, margin:"0 0 2px" }}>Recent Status Activity</p>
        </div>
        {activityApi.loading ? (
          <div style={{ padding:20, color:C.ter, fontSize:13 }}>Loading activity…</div>
        ) : activityLogs.length === 0 ? (
          <div style={{ padding:"24px 20px", textAlign:"center", color:C.ter, fontSize:13 }}>No recent activity found.</div>
        ) : (
          <table className="sp-tbl">
            <thead>
              <tr><th>Event</th><th>Actor</th><th>Request ID</th><th>Created At</th></tr>
            </thead>
            <tbody>
              {activityLogs.map((l: unknown, i: number) => {
                const log = l as Record<string,unknown>;
                return (
                  <tr key={i}>
                    <td style={{ fontFamily:"monospace", fontSize:12 }}>{String(log.action_type ?? log.event ?? "—")}</td>
                    <td style={{ color:C.sub }}>{String(log.actor_role ?? log.actor ?? "system")}</td>
                    <td style={{ color:C.ter, fontFamily:"monospace", fontSize:11 }}>{String(log.request_id ?? "—")}</td>
                    <td style={{ color:C.sub }}>{safeDate(log.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
