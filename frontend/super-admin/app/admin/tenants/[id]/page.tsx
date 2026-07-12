"use client";
import React, { useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, HealthMeter, JobStatusBadge,
  Modal, Input, Skeleton, StatCard, Select,
} from "../../../../components/shared/ui";
import {
  tenantApi, adminTenantsApi, commerceApi, finalRecordsAdminApi, reviewApi, staffApi, bookingsApi,
  serviceAreaAdminApi, serviceabilityApi, mediaApi, authApi, financeApi, usageCreditsAdminApi,
  catalogApi as adminCatalogApi, engineMgmtApi, adminTenantApi,
  adminProviderOnboardingApi, adminOnboardingProvidersApi, adminProviderEnablementApi, adminBookabilityApi,
  type TenantAuditLog,
  type AdminStaffUser, type Booking, type GeoZone, type MediaFile,
  type Deposit, type MatchedTenant, type EnabledService,
  type EffectiveEngineItem, type AdminProviderOnboarding,
  type AdminTenantEnabledOffering, type AdminTenantServiceArea,
  type AdminTenantTeamMember, type AdminTenantAvailabilityRule,
  type ProviderVisibilityStatus, type BookabilityAuditLog,
  type DisputeSettlement,
} from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { useViewport } from "../../../../hooks/useViewport";
import { usePermissions } from "../../../../hooks/usePermissions";
import { SUPER_ADMIN_ONLY } from "../../../../lib/permission-catalog";
import { EntitlementsTab } from "../../../../components/enterprise/EntitlementsTab";
import {
  Building, CreditCard, Banknote, ClipboardCheck,
  Zap, RefreshCw, Star, Clock, CheckCircle2, Users, CalendarCheck, MapPin,
  Camera, Briefcase, Tag, ClipboardList, AlertCircle, ChevronRight,
  ShieldOff, Play,
} from "lucide-react";

type Tab =
  | "overview" | "staff" | "users" | "service-areas" | "enabled-services"
  | "pricing" | "packages" | "wallet" | "deposit" | "disputes" | "settlements" | "risk-health"
  | "media" | "jobs" | "bookings"
  | "reviews" | "audit" | "onboarding"
  | "provider-offerings" | "provider-areas" | "provider-team" | "provider-availability"
  | "bookability" | "entitlements";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "overview",         label: "Overview",          icon: <Building/>        },
  { id: "onboarding",       label: "Onboarding",        icon: <ClipboardList/>   },
  { id: "staff",            label: "Staff",             icon: <Users/>           },
  { id: "users",            label: "Users",             icon: <Users/>           },
  { id: "service-areas",    label: "Service Areas",     icon: <MapPin/>          },
  { id: "enabled-services", label: "Enabled Services",  icon: <Zap/>             },
  { id: "pricing",          label: "Pricing",           icon: <Tag/>             },
  { id: "packages",         label: "Packages & Usage Credits", icon: <Banknote/>        },
  { id: "wallet",           label: "Usage Credit Ledger",   icon: <CreditCard/>      },
  { id: "deposit",          label: "Security Deposit",  icon: <ShieldOff/>       },
  { id: "disputes",         label: "Complaints & Disputes", icon: <AlertCircle/> },
  { id: "settlements",      label: "Customer Credit Settlements", icon: <Banknote/> },
  { id: "risk-health",      label: "Risk & Health",     icon: <Zap/>             },
  { id: "media",            label: "Media / Photos",    icon: <Camera/>          },
  { id: "jobs",             label: "Jobs",              icon: <Briefcase/>       },
  { id: "bookings",         label: "Bookings",          icon: <CalendarCheck/>   },
  { id: "reviews",               label: "Reviews",          icon: <Star/>           },
  { id: "audit",                 label: "Audit Logs",       icon: <Clock/>          },
  { id: "provider-offerings",    label: "Offerings",        icon: <Zap/>            },
  { id: "provider-areas",        label: "Coverage Areas",   icon: <MapPin/>         },
  { id: "provider-team",         label: "Team / Agents",    icon: <Users/>          },
  { id: "provider-availability", label: "Availability",     icon: <Clock/>          },
  { id: "bookability",           label: "Bookability",      icon: <CheckCircle2/>   },
  { id: "entitlements",          label: "Modules & Categories", icon: <Zap/>        },
];

// Grouped tab nav (Part 4 of Tenant 360 redesign) — 23 flat tabs collapsed into
// 7 groups so the sidebar never overflows a single row. Tab ids/bodies unchanged.
const TAB_GROUPS: { key: string; label: string; tabs: Tab[] }[] = [
  { key: "overview",   label: "Overview",       tabs: ["overview"] },
  { key: "setup",      label: "Setup",          tabs: [
    "onboarding", "users", "staff", "service-areas", "enabled-services", "pricing",
    "provider-offerings", "provider-areas", "provider-team", "provider-availability",
    "entitlements",
  ] },
  { key: "operations", label: "Operations",     tabs: ["jobs", "bookings", "disputes", "reviews", "bookability"] },
  { key: "finance",    label: "Finance",        tabs: ["packages", "wallet", "deposit", "settlements"] },
  { key: "trust",      label: "Trust & Quality", tabs: ["risk-health"] },
  { key: "media",      label: "Media",          tabs: ["media"] },
  { key: "audit",      label: "Audit",          tabs: ["audit"] },
];

function groupForTab(t: Tab): typeof TAB_GROUPS[number] {
  return TAB_GROUPS.find(g => g.tabs.includes(t)) ?? TAB_GROUPS[0];
}

// ── Health signal label mapping ────────────────────────────────────────────────
const SIGNAL_LABELS: Record<string, string> = {
  job_completion:            "Job Completion Rate",
  customer_satisfaction:     "Customer Satisfaction",
  warranty_claim:            "Warranty Claim Rate",
  warranty_claim_rate:       "Warranty Claim Rate",
  credit_wallet_health:      "Usage Credit Health",
  usage_credit_health:       "Usage Credit Health",
  response_rate:             "Response Rate",
  cancellation_rate:         "Cancellation Rate",
  booking_fulfillment:       "Booking Fulfillment",
  complaint_rate:            "Complaint Rate",
  rating_score:              "Rating Score",
  sla_compliance:            "SLA Compliance",
};

// ── Status label mapping ───────────────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  pending_setup:     "Pending Setup",
  active:            "Active",
  approved:          "Approved",
  suspended:         "Suspended",
  not_bookable:      "Not Bookable",
  bookable:          "Bookable",
  monthly:           "Monthly",
  gold:              "Gold",
  silver:            "Silver",
  platinum:          "Platinum",
  bronze:            "Bronze",
  starter:           "Starter",
  growth:            "Growth",
  enterprise:        "Enterprise",
  verified:          "Verified",
  pending_review:    "Pending Review",
  changes_requested: "Changes Requested",
  rejected:          "Rejected",
};
function labelOf(raw: string | undefined | null): string {
  if (!raw) return "—";
  return STATUS_LABELS[raw] ?? raw.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// ── Circular progress SVG ─────────────────────────────────────────────────────
function CircularProgress({ pct, size = 88, color = "var(--brand)" }: { pct: number; size?: number; color?: string }) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <svg width={size} height={size} style={{ flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={8}/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}/>
      <text x={size/2} y={size/2 + 5} textAnchor="middle" fontSize={size < 70 ? 13 : 16}
        fontWeight={800} fill="var(--text-primary)">{pct}%</text>
    </svg>
  );
}

const menuItemStyle: React.CSSProperties = {
  display: "block", width: "100%", textAlign: "left", padding: "10px 14px",
  border: "none", background: "none", cursor: "pointer", fontSize: 13,
  color: "var(--text-primary)",
};

const selectStyle: React.CSSProperties = {
  width: "100%", height: 40, padding: "0 12px", borderRadius: 10,
  border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", fontSize: 13, outline: "none",
};

const BOOKING_VARIANT: Record<string, "default"|"success"|"warning"|"danger"|"info"|"muted"> = {
  pending_confirmation: "warning",
  confirmed: "success",
  cancelled: "danger",
  converted: "info",
  no_show: "muted",
  void: "muted",
};

// ── Onboarding Admin Tab ──────────────────────────────────────────────────────
function OnboardingAdminTab({ tenantId }: { tenantId: string }) {
  const perm = usePermissions();
  const onboarding = useApi(useCallback(() => adminProviderOnboardingApi.get(tenantId), [tenantId]), [tenantId]);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [toastErr, setToastErr] = useState<string | null>(null);

  function flash(msg: string, err = false) {
    if (err) { setToastErr(msg); setTimeout(() => setToastErr(null), 4000); }
    else     { setToast(msg);    setTimeout(() => setToast(null), 3000); }
  }

  const refreshAction = useAction(useCallback(async () => {
    await adminProviderOnboardingApi.refresh(tenantId);
    onboarding.refetch();
    flash("Onboarding refreshed.");
  }, [tenantId, onboarding]));

  const approveAction = useAction(useCallback(async () => {
    await adminOnboardingProvidersApi.approve(tenantId);
    onboarding.refetch();
    flash("Provider approved.");
  }, [tenantId, onboarding]));

  const rejectAction = useAction(useCallback(async () => {
    if (!rejectReason.trim()) { flash("A reason is required to reject.", true); return; }
    await adminOnboardingProvidersApi.reject(tenantId, rejectReason);
    onboarding.refetch();
    setRejectOpen(false); setRejectReason("");
    flash("Provider rejected.");
  }, [tenantId, rejectReason, onboarding]));

  const d: AdminProviderOnboarding | null = onboarding.data ?? null;

  const REVIEW_VARIANT: Record<string, "success"|"warning"|"danger"|"muted"|"info"> = {
    approved: "success", pending_review: "warning", not_submitted: "muted",
    rejected: "danger", changes_requested: "warning",
  };

  if (onboarding.loading) return <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
    <Skeleton height={160}/><Skeleton height={300}/>
  </div>;

  if (onboarding.error) return (
    <Card>
      <div style={{ textAlign:"center", padding:"32px 0" }}>
        <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
        <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{onboarding.error}</p>
        <Btn size="sm" variant="primary" onClick={onboarding.refetch}>Retry</Btn>
      </div>
    </Card>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {toast    && <div style={{ padding:"10px 16px", borderRadius:10, background:"rgba(5,150,105,0.08)",
        border:"1px solid rgba(5,150,105,0.25)", fontSize:13, color:"#059669" }}>{toast}</div>}
      {toastErr && <div style={{ padding:"10px 16px", borderRadius:10, background:"rgba(220,38,38,0.08)",
        border:"1px solid rgba(220,38,38,0.25)", fontSize:13, color:"#dc2626" }}>{toastErr}</div>}

      {/* Summary card */}
      {d && (
        <Card>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start",
            marginBottom:16, flexWrap:"wrap", gap:12 }}>
            <div>
              <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 4px", fontWeight:500 }}>
                {d.business_name ?? d.tenant_name ?? "Provider"} — {d.category_name ?? d.vertical_type ?? "Uncategorised"}
              </p>
              <h3 style={{ fontSize:18, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                {d.profile_completion_percentage}% Profile Complete
              </h3>
            </div>
            <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
              <Badge variant={REVIEW_VARIANT[d.review_status] ?? "muted"}>
                {d.review_status.replace(/_/g, " ")}
              </Badge>
              {/* FINAL-L5-05P: Refresh's backend endpoint requires
                  super_admin (not yet granular); Approve/Reject require
                  the real, distinct tenants.approve/tenants.reject
                  permissions -- gated individually, not by page-read
                  permission alone. */}
              {perm.role === "super_admin" && (
                <Btn size="sm" variant="secondary" loading={refreshAction.loading}
                  onClick={() => refreshAction.execute()}>
                  <RefreshCw size={12}/> Refresh
                </Btn>
              )}
              {d.review_status !== "approved" && (
                <>
                  {perm.has("tenants.approve") && (
                    <Btn size="sm" variant="primary" loading={approveAction.loading}
                      disabled={d.profile_completion_percentage < 100}
                      onClick={() => approveAction.execute()}>
                      Approve
                    </Btn>
                  )}
                  {perm.has("tenants.reject") && (
                    <Btn size="sm" variant="danger" onClick={() => setRejectOpen(true)}>Reject</Btn>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div style={{ height:8, background:"var(--surface-sunken)", borderRadius:99,
            overflow:"hidden", border:"1px solid var(--border)", marginBottom:16 }}>
            <div style={{ height:"100%", borderRadius:99,
              width:`${Math.max(0, Math.min(100, d.profile_completion_percentage))}%`,
              background: d.profile_completion_percentage >= 100 ? "#059669" : d.profile_completion_percentage >= 60 ? "#d97706" : "#2563eb",
              transition:"width 0.4s" }}/>
          </div>
          {d.profile_completion_percentage < 100 && (
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 16px" }}>
              Approval is disabled until profile completion reaches 100%.
            </p>
          )}

          {/* Status row */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(120px,1fr))", gap:10 }}>
            {[
              { label:"Onboarding Status", value: d.onboarding_status?.replace(/_/g," ") ?? "—" },
              { label:"Readiness",         value: d.readiness_status?.replace(/_/g," ") ?? "—" },
              { label:"Bookable Status",   value: d.bookable_status?.replace(/_/g," ") ?? "—" },
              { label:"Verification",      value: d.verification_status?.replace(/_/g," ") ?? "not started" },
              { label:"Package",           value: d.selected_package_name ?? "None selected" },
              { label:"Package Status",    value: d.package_status?.replace(/_/g," ") ?? "—" },
            ].map(s => (
              <div key={s.label} style={{ background:"var(--surface-sunken)", borderRadius:10,
                padding:"10px 12px", border:"1px solid var(--border)" }}>
                <p style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)", margin:0, textTransform:"capitalize" }}>{s.value}</p>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{s.label}</p>
              </div>
            ))}
          </div>

          {/* Contact / location */}
          <div style={{ marginTop:16, paddingTop:16, borderTop:"1px solid var(--border)",
            display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(140px,1fr))", gap:10 }}>
            {[
              ["Owner", d.owner_name ?? "—"],
              ["Owner Email", d.owner_email ?? "—"],
              ["City", d.city ?? "—"],
              ["State", d.state ?? "—"],
              ["District", d.district ?? "—"],
              ["Zipcode", d.zipcode ?? "—"],
            ].map(([label, val]) => (
              <div key={label}>
                <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 2px", textTransform:"uppercase", letterSpacing:"0.04em" }}>{label}</p>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{val}</p>
              </div>
            ))}
          </div>

          {d.updated_at && (
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"16px 0 0" }}>
              Last updated {new Date(d.updated_at).toLocaleString()}
            </p>
          )}
        </Card>
      )}

      {/* Reject modal */}
      <Modal open={rejectOpen} title="Reject Provider Onboarding" onClose={() => setRejectOpen(false)} size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            This will reject onboarding for this provider. This action is logged.
          </p>
          <div>
            <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)",
              display:"block", marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>
              Reason *
            </label>
            <textarea rows={3} value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              style={{ width:"100%", fontSize:13, padding:"8px 10px", borderRadius:8,
                border:"1px solid var(--border)", background:"var(--surface)",
                color:"var(--text-primary)", resize:"vertical", boxSizing:"border-box" }}
              placeholder="Reason for rejection…"/>
          </div>
          {rejectAction.error && (
            <p style={{ fontSize:12, color:"#dc2626", margin:0 }}>{rejectAction.error}</p>
          )}
          <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
            <Btn size="sm" variant="secondary" onClick={() => setRejectOpen(false)}>Cancel</Btn>
            <Btn size="sm" variant="danger" loading={rejectAction.loading} disabled={!rejectReason.trim()}
              onClick={() => rejectAction.execute()}>
              Confirm Reject
            </Btn>
          </div>
        </div>
      </Modal>

      {!d && !onboarding.loading && (
        <Card>
          <div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)" }}>
            <ClipboardList size={28} style={{ display:"block", margin:"0 auto 10px" }}/>
            <p style={{ fontSize:13, margin:0 }}>No onboarding record found for this provider.</p>
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Admin Provider Offerings Tab ─────────────────────────────────────────────
function ProviderOfferingsTab({ tenantId }: { tenantId: string }) {
  const perm = usePermissions();
  const offerings = useApi(useCallback(() => adminProviderEnablementApi.listOfferings(tenantId), [tenantId]));
  const [suspendId,     setSuspendId]     = useState<string | null>(null);
  const [suspendReason, setSuspendReason] = useState("");
  const [toast,    setToast]    = useState<string | null>(null);
  const [toastErr, setToastErr] = useState<string | null>(null);

  function flash(msg: string, err = false) {
    if (err) { setToastErr(msg); setTimeout(() => setToastErr(null), 4000); }
    else     { setToast(msg);    setTimeout(() => setToast(null), 3000); }
  }

  const refreshAllAction = useAction(useCallback(async () => {
    await adminProviderEnablementApi.refreshReadiness(tenantId);
    offerings.refetch();
    flash("Readiness refreshed for all offerings.");
  }, [tenantId, offerings]));

  const suspendAction = useAction(useCallback(async () => {
    if (!suspendId) return;
    if (!suspendReason.trim()) { flash("A reason is required.", true); return; }
    await adminProviderEnablementApi.suspendOffering(tenantId, suspendId, suspendReason);
    offerings.refetch();
    setSuspendId(null);
    setSuspendReason("");
    flash("Offering suspended.");
  }, [tenantId, suspendId, suspendReason, offerings]));

  const reactivateAction = useAction(useCallback(async (id: string) => {
    await adminProviderEnablementApi.reactivateOffering(tenantId, id);
    offerings.refetch();
    flash("Offering reactivated.");
  }, [tenantId, offerings]));

  const STATUS_V: Record<string, "success"|"warning"|"danger"|"muted"|"info"> = {
    active: "success", draft: "muted", inactive: "warning", suspended: "danger", rejected: "danger",
  };
  const READINESS_V: Record<string, "success"|"warning"|"danger"|"muted"> = {
    ready: "success", not_ready: "warning", blocked: "danger",
  };

  const list: AdminTenantEnabledOffering[] = offerings.data?.offerings ?? [];

  if (offerings.loading) return <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
    {[...Array(4)].map((_,i) => <Skeleton key={i} height={52}/>)}
  </div>;

  if (offerings.error) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0" }}>
      <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
      <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{offerings.error}</p>
      <Btn size="sm" variant="primary" onClick={offerings.refetch}>Retry</Btn>
    </div></Card>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      {toast    && <div style={{ padding:"10px 16px", borderRadius:10, background:"rgba(5,150,105,0.08)",
        border:"1px solid rgba(5,150,105,0.25)", fontSize:13, color:"#059669" }}>✓ {toast}</div>}
      {toastErr && <div style={{ padding:"10px 16px", borderRadius:10, background:"rgba(220,38,38,0.08)",
        border:"1px solid rgba(220,38,38,0.25)", fontSize:13, color:"#dc2626" }}>✕ {toastErr}</div>}

      {/* FINAL-L5-05P: refresh-readiness/suspend/reactivate all require
          super_admin on the backend (not yet granular) -- gated by role,
          not page-read permission alone. */}
      {perm.role === "super_admin" && (
        <div style={{ display:"flex", justifyContent:"flex-end" }}>
          <Btn size="sm" variant="secondary" loading={refreshAllAction.loading}
            onClick={() => refreshAllAction.execute()}>
            <RefreshCw size={12}/> Refresh All Readiness
          </Btn>
        </div>
      )}

      {list.length === 0 ? (
        <Card><div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)" }}>
          <Zap size={28} style={{ display:"block", margin:"0 auto 10px", opacity:0.4 }}/>
          <p style={{ fontSize:13, margin:0 }}>No offerings enabled by this provider.</p>
        </div></Card>
      ) : (
        <Card padding={0}>
          <div style={{ overflowX:"auto" }}>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Offering","Type","Status","Readiness","Emerg.","Price","Activated","Blockers","Actions"].map(h => (
                    <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                      whiteSpace:"nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((o, i) => (
                  <tr key={o.provider_enabled_offering_id}
                    style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding:"10px 12px", fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                      {o.offering_name}
                    </td>
                    <td style={{ padding:"10px 12px" }}>
                      <Badge variant="muted" size="sm">{o.offering_type?.replace(/_/g," ") ?? "—"}</Badge>
                    </td>
                    <td style={{ padding:"10px 12px" }}>
                      <Badge variant={STATUS_V[o.status] ?? "muted"} size="sm">{o.status}</Badge>
                    </td>
                    <td style={{ padding:"10px 12px" }}>
                      {o.readiness_status ? (
                        <Badge variant={READINESS_V[o.readiness_status] ?? "muted"} size="sm">
                          {o.readiness_status.replace(/_/g," ")}
                        </Badge>
                      ) : <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>—</span>}
                    </td>
                    <td style={{ padding:"10px 12px" }}>
                      <Badge variant={o.supports_emergency ? "success" : "muted"} size="sm">
                        {o.supports_emergency ? "Yes" : "No"}
                      </Badge>
                    </td>
                    <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                      {o.provider_price_override ? `₹${parseFloat(o.provider_price_override).toLocaleString("en-IN")}` : "—"}
                    </td>
                    <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-secondary)" }}>
                      {o.activated_at ? new Date(o.activated_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding:"10px 12px", maxWidth:160 }}>
                      {o.readiness_blockers && o.readiness_blockers.length > 0 ? (
                        <div style={{ display:"flex", flexDirection:"column", gap:2 }}>
                          {o.readiness_blockers.slice(0,2).map((b, bi) => (
                            <span key={bi} style={{ fontSize:10, color:"#dc2626" }}>{b.message}</span>
                          ))}
                          {o.readiness_blockers.length > 2 && (
                            <span style={{ fontSize:10, color:"var(--text-tertiary)" }}>
                              +{o.readiness_blockers.length-2} more
                            </span>
                          )}
                        </div>
                      ) : <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>—</span>}
                    </td>
                    <td style={{ padding:"10px 12px" }}>
                      <div style={{ display:"flex", gap:4 }}>
                        {perm.role === "super_admin" && (o.status !== "suspended" ? (
                          <Btn size="xs" variant="ghost"
                            onClick={() => { setSuspendId(o.provider_enabled_offering_id); setSuspendReason(""); }}>
                            <ShieldOff size={11}/> Suspend
                          </Btn>
                        ) : (
                          <Btn size="xs" variant="ghost" loading={reactivateAction.loading}
                            onClick={() => reactivateAction.execute(o.provider_enabled_offering_id)}>
                            <Play size={11}/> Reactivate
                          </Btn>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Suspend Modal */}
      {suspendId && (
        <Modal open title="Suspend Offering" onClose={() => setSuspendId(null)} size="sm">
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              The provider will be notified. Provide a clear reason.
            </p>
            <div>
              <label style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", display:"block",
                marginBottom:6, textTransform:"uppercase", letterSpacing:"0.06em" }}>Reason *</label>
              <textarea rows={3} value={suspendReason} onChange={e => setSuspendReason(e.target.value)}
                style={{ width:"100%", fontSize:13, padding:"8px 10px", borderRadius:8,
                  border:"1px solid var(--border)", background:"var(--surface)", color:"var(--text-primary)",
                  resize:"vertical" }}
                placeholder="Policy violation, quality issue…"/>
            </div>
            {suspendAction.error && (
              <p style={{ fontSize:12, color:"#dc2626", margin:0 }}>{suspendAction.error}</p>
            )}
            <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
              <Btn size="sm" variant="secondary" onClick={() => setSuspendId(null)}>Cancel</Btn>
              <Btn size="sm" variant="primary" loading={suspendAction.loading}
                onClick={() => suspendAction.execute()}>
                Confirm Suspend
              </Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Admin Provider Coverage Areas Tab (read-only) ─────────────────────────────
function ProviderAreasTab({ tenantId, refreshToken }: { tenantId: string; refreshToken?: number }) {
  const areas = useApi(useCallback(() => adminProviderEnablementApi.listServiceAreas(tenantId), [tenantId, refreshToken]));
  const list: AdminTenantServiceArea[] = areas.data?.areas ?? [];

  if (areas.loading) return <Skeleton height={200}/>;
  if (areas.error) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0" }}>
      <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
      <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{areas.error}</p>
      <Btn size="sm" variant="primary" onClick={areas.refetch}>Retry</Btn>
    </div></Card>
  );
  if (list.length === 0) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)" }}>
      <MapPin size={28} style={{ display:"block", margin:"0 auto 10px", opacity:0.4 }}/>
      <p style={{ fontSize:13, margin:0 }}>No service areas configured by this provider.</p>
    </div></Card>
  );

  return (
    <Card padding={0}>
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Type","State","District","City","Zipcode","Zone","Radius","Primary","Active","Created"].map(h => (
                <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                  color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                  whiteSpace:"nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((a, i) => (
              <tr key={a.id}
                style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant="muted" size="sm">{a.coverage_type}</Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{a.state ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{a.district ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{a.city ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, fontFamily:"monospace", color:"var(--text-secondary)" }}>{a.zipcode ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{a.zone_name ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                  {a.radius_km ? `${a.radius_km} km` : "—"}
                </td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant={a.is_primary ? "info" : "muted"} size="sm">
                    {a.is_primary ? "Primary" : "—"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant={a.is_active ? "success" : "muted"} size="sm">
                    {a.is_active ? "Active" : "Off"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-tertiary)" }}>
                  {a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Admin Provider Team Tab (read-only) ───────────────────────────────────────
function ProviderTeamTab({ tenantId }: { tenantId: string }) {
  const team = useApi(useCallback(() => adminProviderEnablementApi.listTeamMembers(tenantId), [tenantId]));
  const list: AdminTenantTeamMember[] = team.data?.members ?? [];

  if (team.loading) return <Skeleton height={200}/>;
  if (team.error) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0" }}>
      <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
      <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{team.error}</p>
      <Btn size="sm" variant="primary" onClick={team.refetch}>Retry</Btn>
    </div></Card>
  );
  if (list.length === 0) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)" }}>
      <Users size={28} style={{ display:"block", margin:"0 auto 10px", opacity:0.4 }}/>
      <p style={{ fontSize:13, margin:0 }}>No team members registered by this provider.</p>
    </div></Card>
  );

  return (
    <Card padding={0}>
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Name","Type","Phone","Email","Designation","Assignments","Status","Created"].map(h => (
                <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                  color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                  whiteSpace:"nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((m, i) => (
              <tr key={m.member_id}
                style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding:"10px 12px", fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                  {m.full_name}
                </td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant="muted" size="sm">{m.member_type}</Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{m.phone ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{m.email ?? "—"}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>{m.designation ?? "—"}</td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant={m.can_receive_assignment ? "success" : "muted"} size="sm">
                    {m.can_receive_assignment ? "Yes" : "No"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant={m.status === "active" ? "success" : "muted"} size="sm">{m.status}</Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-tertiary)" }}>
                  {m.created_at ? new Date(m.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Admin Provider Availability Tab (read-only) ───────────────────────────────
const DAYS_SHORT = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function ProviderAvailabilityTab({ tenantId }: { tenantId: string }) {
  const avail = useApi(useCallback(() => adminProviderEnablementApi.listAvailability(tenantId), [tenantId]));
  const list: AdminTenantAvailabilityRule[] = avail.data?.rules ?? [];

  if (avail.loading) return <Skeleton height={200}/>;
  if (avail.error) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0" }}>
      <AlertCircle size={28} style={{ color:"#dc2626", display:"block", margin:"0 auto 10px" }}/>
      <p style={{ fontSize:13, color:"#dc2626", margin:"0 0 12px" }}>{avail.error}</p>
      <Btn size="sm" variant="primary" onClick={avail.refetch}>Retry</Btn>
    </div></Card>
  );
  if (list.length === 0) return (
    <Card><div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-tertiary)" }}>
      <Clock size={28} style={{ display:"block", margin:"0 auto 10px", opacity:0.4 }}/>
      <p style={{ fontSize:13, margin:0 }}>No availability rules configured by this provider.</p>
    </div></Card>
  );

  return (
    <Card padding={0}>
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
              {["Scope","Scope Name","Day","Start","End","Slot (min)","Max/Slot","Active","Created"].map(h => (
                <th key={h} style={{ padding:"9px 12px", textAlign:"left", fontSize:10, fontWeight:700,
                  color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em",
                  whiteSpace:"nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((r, i) => (
              <tr key={r.availability_id}
                style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant="muted" size="sm">{r.scope_type.replace(/_/g," ")}</Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                  {r.scope_name ?? (r.scope_id ? r.scope_id.slice(0,8)+"…" : "—")}
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>
                  {DAYS_SHORT[r.day_of_week] ?? r.day_of_week}
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, fontFamily:"monospace" }}>{r.start_time}</td>
                <td style={{ padding:"10px 12px", fontSize:12, fontFamily:"monospace" }}>{r.end_time}</td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                  {r.slot_duration_minutes ?? "—"}
                </td>
                <td style={{ padding:"10px 12px", fontSize:12, color:"var(--text-secondary)" }}>
                  {r.max_bookings_per_slot ?? "—"}
                </td>
                <td style={{ padding:"10px 12px" }}>
                  <Badge variant={r.is_active ? "success" : "muted"} size="sm">
                    {r.is_active ? "Active" : "Off"}
                  </Badge>
                </td>
                <td style={{ padding:"10px 12px", fontSize:11, color:"var(--text-tertiary)" }}>
                  {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Admin Bookability Tab ─────────────────────────────────────────────────────
function BookabilityTab({ tenantId }: { tenantId: string }) {
  const perm = usePermissions();
  const status    = useApi(useCallback(() => adminBookabilityApi.getProvider(tenantId), [tenantId]));
  const auditLogs = useApi(useCallback(() => adminBookabilityApi.getAuditLogs(tenantId, 20), [tenantId]));

  const [overrideModal, setOverrideModal] = useState<"visible" | "bookable" | null>(null);
  const [overrideValue,  setOverrideValue]  = useState<"true" | "false">("true");
  const [overrideReason, setOverrideReason] = useState("");

  const refreshAction = useAction(
    useCallback(() => adminBookabilityApi.refreshProvider(tenantId), [tenantId])
  );

  const overrideVisAction = useAction(
    useCallback(
      () => adminBookabilityApi.overrideVisibility(tenantId, overrideValue === "true", overrideReason),
      [tenantId, overrideValue, overrideReason]
    )
  );
  const overrideBkAction = useAction(
    useCallback(
      () => adminBookabilityApi.overrideBookability(tenantId, overrideValue === "true", overrideReason),
      [tenantId, overrideValue, overrideReason]
    )
  );
  const removeVisAction = useAction(
    useCallback(() => adminBookabilityApi.removeVisibilityOverride(tenantId), [tenantId])
  );
  const removeBkAction = useAction(
    useCallback(() => adminBookabilityApi.removeBookabilityOverride(tenantId), [tenantId])
  );

  const s: ProviderVisibilityStatus | null = status.data ?? null;
  const logs: BookabilityAuditLog[] = auditLogs.data?.logs ?? [];

  if (status.loading) return <Skeleton height={300} />;
  if (status.error) return (
    <Card padding={24}>
      <p style={{ color: "#dc2626", fontSize: 13 }}>{status.error}</p>
      <Btn size="sm" variant="primary" onClick={() => status.refetch()}>Retry</Btn>
    </Card>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Status cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px", textTransform: "uppercase", letterSpacing: "0.06em" }}>Visibility</p>
              <Badge variant={s?.is_visible ? "success" : "warning"} size="sm">
                {s?.is_visible ? "Visible to Customers" : "Hidden from Customers"}
              </Badge>
              {s?.override_is_visible !== null && s?.override_is_visible !== undefined && (
                <p style={{ fontSize: 10, color: "#d97706", margin: "4px 0 0" }}>Admin override active: {s.override_visible_reason}</p>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {/* FINAL-L5-05P: override-visibility/override-bookability
                  previously accepted ANY authenticated principal on the
                  backend (a real P0 fix, now require_super_admin) --
                  frontend gated to match, not left to page-read permission. */}
              {perm.role === "super_admin" && (
                <Btn size="sm" variant="secondary" onClick={() => { setOverrideModal("visible"); setOverrideReason(""); }}>Override</Btn>
              )}
              {perm.role === "super_admin" && s?.override_is_visible !== null && s?.override_is_visible !== undefined && (
                <Btn size="sm" variant="secondary" onClick={() => removeVisAction.execute().then(() => status.refetch())} disabled={removeVisAction.loading}>Remove Override</Btn>
              )}
            </div>
          </div>
          {(s?.visibility_blockers?.length ?? 0) > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 6px" }}>Blockers:</p>
              {s!.visibility_blockers.map((b, i) => (
                <p key={i} style={{ fontSize: 11, color: "#dc2626", margin: "2px 0" }}>• {b.message}</p>
              ))}
            </div>
          )}
        </Card>

        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px", textTransform: "uppercase", letterSpacing: "0.06em" }}>Bookability</p>
              <Badge variant={s?.is_bookable ? "success" : "danger"} size="sm">
                {s?.is_bookable ? "Bookable" : "Not Bookable"}
              </Badge>
              {s?.override_is_bookable !== null && s?.override_is_bookable !== undefined && (
                <p style={{ fontSize: 10, color: "#d97706", margin: "4px 0 0" }}>Admin override active: {s.override_bookable_reason}</p>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {perm.role === "super_admin" && (
                <Btn size="sm" variant="secondary" onClick={() => { setOverrideModal("bookable"); setOverrideReason(""); }}>Override</Btn>
              )}
              {perm.role === "super_admin" && s?.override_is_bookable !== null && s?.override_is_bookable !== undefined && (
                <Btn size="sm" variant="secondary" onClick={() => removeBkAction.execute().then(() => status.refetch())} disabled={removeBkAction.loading}>Remove Override</Btn>
              )}
            </div>
          </div>
          {(s?.bookability_blockers?.length ?? 0) > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 6px" }}>Blockers:</p>
              {s!.bookability_blockers.map((b, i) => (
                <p key={i} style={{ fontSize: 11, color: "#dc2626", margin: "2px 0" }}>• {b.message}</p>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8 }}>
        {perm.role === "super_admin" && (
          <Btn size="sm" variant="secondary" onClick={() => refreshAction.execute().then(() => status.refetch())} disabled={refreshAction.loading}>
            <RefreshCw size={13} /> {refreshAction.loading ? "Re-evaluating…" : "Re-evaluate Now"}
          </Btn>
        )}
        <span style={{ fontSize: 12, color: "var(--text-tertiary)", alignSelf: "center" }}>
          Last evaluated: {s?.last_evaluated_at ? new Date(s.last_evaluated_at).toLocaleString() : "Never"}
        </span>
      </div>

      {/* Audit Logs */}
      <Card padding={0}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
          Audit Log
        </div>
        {logs.length === 0 ? (
          <p style={{ padding: 20, fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>No audit events yet.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Event", "Trigger", "Actor", "Date"].map(h => (
                    <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700,
                      color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => (
                  <tr key={log.id} style={{ borderBottom: i < logs.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-primary)", fontFamily: "monospace" }}>{log.event_type}</td>
                    <td style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-secondary)" }}>{log.trigger_source ?? "—"}</td>
                    <td style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-secondary)" }}>{log.actor_type ?? "—"}</td>
                    <td style={{ padding: "8px 14px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Override Modal */}
      <Modal
        open={overrideModal !== null}
        onClose={() => setOverrideModal(null)}
        title={overrideModal === "visible" ? "Override Visibility" : "Override Bookability"}
        size="sm"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Select
            value={overrideValue}
            onChange={v => setOverrideValue(v as "true" | "false")}
            options={[{ value: "true", label: "Force Enable" }, { value: "false", label: "Force Disable" }]}
            placeholder="Select override"
          />
          <Input
            label="Reason (required)"
            value={overrideReason}
            onChange={v => setOverrideReason(v)}
            placeholder="Explain why this override is needed…"
          />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn size="sm" variant="secondary" onClick={() => setOverrideModal(null)}>Cancel</Btn>
            <Btn
              size="sm"
              variant="primary"
              disabled={!overrideReason.trim() || (overrideModal === "visible" ? overrideVisAction.loading : overrideBkAction.loading)}
              onClick={() => (overrideModal === "visible" ? overrideVisAction.execute() : overrideBkAction.execute()).then(() => { setOverrideModal(null); status.refetch(); })}
            >
              Apply Override
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ── Effective Engines read-only card ─────────────────────────────────────────
function EffectiveEnginesCard({ tenantId }: { tenantId: string }) {
  const { data, loading } = useApi(useCallback(() => engineMgmtApi.getEffectiveEngines(tenantId), [tenantId]));
  const engines  = data?.engines ?? [];
  const enabled  = engines.filter((e: any) => e.effective_enabled ?? e.is_enabled);
  const disabled = engines.filter((e: any) => !(e.effective_enabled ?? e.is_enabled));

  const SOURCE_LABEL: Record<string, string> = {
    global:              "Global",
    category:            "Category",
    package_entitlement: "Package",
    tenant_override:     "Override",
  };

  return (
    <Card padding={0}>
      <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
        display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
          Effective Engines
        </h3>
        <div style={{ display:"flex", gap:12, alignItems:"center" }}>
          {data && (
            <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
              {enabled.length} enabled / {data.summary?.total ?? engines.length} total
            </span>
          )}
          <a href="/admin/engines" style={{ fontSize:12, color:"var(--text-link)", textDecoration:"none" }}>
            Manage →
          </a>
        </div>
      </div>

      {loading ? (
        <div style={{ padding:"12px 20px" }}>Loading…</div>
      ) : (
        <div style={{ padding:"12px 20px" }}>
          {data?.category && (
            <p style={{ fontSize:11, color:"var(--text-tertiary)", marginBottom:10, marginTop:0 }}>
              Category: <strong>{data.category.name}</strong>
              {data.package && <> · Package: <strong>{data.package.name}</strong></>}
            </p>
          )}

          {/* Enabled engines */}
          {enabled.length > 0 && (
            <div style={{ marginBottom:12 }}>
              <p style={{ fontSize:11, fontWeight:700, color:"var(--success-text)", marginBottom:6, marginTop:0 }}>
                Enabled ({enabled.length})
              </p>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {enabled.map((e: any) => (
                  <span key={e.engine_key ?? e.engine_id}
                    style={{ display:"inline-flex", alignItems:"center", gap:4, padding:"2px 8px",
                      borderRadius:6, border:"1px solid var(--success-border)",
                      background:"var(--success-bg)", fontSize:11, color:"var(--success-text)" }}>
                    {e.engine_key ?? e.name}
                    {e.source && e.source !== "global" && (
                      <span style={{ fontSize:10, opacity:0.7 }}>·{SOURCE_LABEL[e.source]}</span>
                    )}
                    {e.is_required && <span style={{ fontSize:10, fontWeight:700 }}>*</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Disabled engines (collapsed) */}
          {disabled.length > 0 && (
            <details style={{ cursor:"pointer" }}>
              <summary style={{ fontSize:11, fontWeight:600, color:"var(--text-tertiary)", listStyle:"none", marginBottom:6 }}>
                ▸ Disabled ({disabled.length})
              </summary>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginTop:6 }}>
                {disabled.map((e: any) => (
                  <span key={e.engine_key ?? e.engine_id}
                    style={{ display:"inline-flex", alignItems:"center", gap:4, padding:"2px 8px",
                      borderRadius:6, border:"1px solid var(--border)",
                      background:"var(--surface-sunken)", fontSize:11, color:"var(--text-tertiary)" }}>
                    {e.engine_key ?? e.name}
                    {e.reason && <span style={{ fontSize:10 }}>· {e.reason.slice(0, 25)}</span>}
                  </span>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </Card>
  );
}

const VALID_TAB_IDS = new Set<string>(TABS.map(t => t.id));
// Aliases for legacy/loosely-named links (e.g. tenants list "Review Verification" action).
const TAB_ALIASES: Record<string, Tab> = {
  verification: "onboarding",
  verify: "onboarding",
};
function resolveInitialTab(raw: string | null): Tab {
  if (!raw) return "overview";
  if (VALID_TAB_IDS.has(raw)) return raw as Tab;
  if (TAB_ALIASES[raw]) return TAB_ALIASES[raw];
  return "overview";
}

function Tenant360PageInner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const perm = usePermissions();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => resolveInitialTab(searchParams.get("tab")));
  const viewport = useViewport();
  const isMobile = viewport === "mobile";
  const isTablet = viewport === "tablet";
  const kpiCols = isMobile ? 1 : isTablet ? 2 : 4;
  const overviewCols = isMobile || isTablet ? "1fr" : "2fr 1fr";

  // ── Core data (always loaded) ─────────────────────────────────────────────
  const tenant   = useApi(useCallback(() => tenantApi.get(id),                              [id]), [id]);
  // NOTE (E2E-05 fix): previously called commerceApi.walletBalance(id), which reads the separate
  // (legacy/unused) tenant_wallets table — that table shows credit_balance=0.00 for the demo tenant
  // while the authoritative usage-credit system (tenant_billing/usage_credit_ledger, surfaced on
  // /admin/finance/usage-credits) shows 3958.00. Repointed to the same authoritative ledger endpoint
  // so this page's "Usage Credit Ledger" tab and KPI/readiness checks match the Usage Credits page.
  const wallet   = useApi(useCallback(() => usageCreditsAdminApi.getTenantLedger(id),       [id]), [id]);
  const revAgg   = useApi(useCallback(() => reviewApi.getAggregate("tenant", id),           [id]), [id]);

  // ── Tab data (all eager so switching is instant) ──────────────────────────
  const health      = useApi(useCallback(() => tenantApi.getHealth(id),                     [id]));
  const billing     = useApi(useCallback(() => tenantApi.getBillingInfo(id),                [id]));
  const flags       = useApi(useCallback(() => tenantApi.getFeatureFlags(id),               [id]));
  const invoices    = useApi(useCallback(() => tenantApi.getBillingInvoices(id, 5),         [id]));
  const recentJobs  = useApi(useCallback(() => finalRecordsAdminApi.listForTenant(id, 5),[id]));
  const recentBkgs  = useApi(useCallback(() => bookingsApi.list(id, { limit: "5" }),        [id]));

  const staff       = useApi(useCallback(() => staffApi.adminList(id),                      [id]));
  const users       = useApi(useCallback(() => authApi.listUsers({ tenant_id: id, limit: 100 }), [id]));
  const zones       = useApi(useCallback(() => serviceAreaAdminApi.listByTenant(id),        [id]));
  const enabledSvcs = useApi(useCallback(() => adminCatalogApi.listEnabledServices(id),     [id]));
  const pricing     = useApi(useCallback(() => adminCatalogApi.listPricingRules(),          []));
  const deposit     = useApi(useCallback(() => commerceApi.getDeposit(id),                  [id]));
  const depositTxns = useApi(useCallback(() => commerceApi.depositTransactions(id),         [id]));
  const packages    = useApi(useCallback(() => commerceApi.listPackages(),                  []));
  // txns reuses the same authoritative ledger fetch (see `wallet` above) instead of the
  // legacy commerceApi.walletTransactions(id) which read the disconnected tenant_wallets ledger.
  const txns        = useApi(useCallback(() => usageCreditsAdminApi.getTenantLedger(id),    [id]));
  const settlements = useApi(useCallback(() => financeApi.listSettlements({ tenantId: id, limit: 50 }), [id]), [id]);
  const penalties   = useApi(useCallback(() => financeApi.listPenalties({ tenantId: id, limit: 50 }),   [id]), [id]);
  const media       = useApi(useCallback(() => mediaApi.listFiles(id, { limit: 50 }),       [id]));
  const mediaQuota  = useApi(useCallback(() => mediaApi.getQuota(id),                       [id]));
  const allJobs     = useApi(useCallback(() => finalRecordsAdminApi.listForTenant(id, 30),[id]));
  const allBookings = useApi(useCallback(() => bookingsApi.list(id, { limit: "30" }),       [id]));
  const allReviews  = useApi(useCallback(() => reviewApi.listByTenant(id, 30),              [id]));
  const audit       = useApi(useCallback(() => tenantApi.getAuditLog(id, { limit: 20 }),   [id]));

  // ── Mutations ──────────────────────────────────────────────────────────────
  const creditAction        = useAction(useCallback((amount: number, reason: string) =>
    adminTenantsApi.addUsageCredits(id, amount, reason), [id]));
  const suspendAction       = useAction(useCallback((reason: string) =>
    adminTenantsApi.suspend(id, reason), [id]));
  const reinstateAction     = useAction(useCallback((reason: string) =>
    adminTenantsApi.reactivate(id, reason), [id]));
  const upgradePlanAction   = useAction(useCallback((plan: string, reason: string) =>
    adminTenantsApi.changePlan(id, plan, reason), [id]));
  const adjustDepositAction = useAction(useCallback((amount: number, reason: string, category: "goodwill"|"dispute"|"correction"|"refund") =>
    commerceApi.adminAdjustDeposit(id, amount, reason, category), [id]));
  const deactivateStaffAction = useAction(useCallback((userId: string) =>
    staffApi.deactivate(userId), [id]));
  const deleteMediaAction   = useAction(useCallback((fileId: string) =>
    mediaApi.deleteFile(id, fileId), [id]));

  // Sprint 4 — new staff / user / service-area mutations
  const addStaffAction  = useAction(useCallback((data: { name:string; email:string; phone:string }) =>
    adminTenantApi.createStaff(id, data), [id]));
  const addUserAction   = useAction(useCallback((data: { name:string; email:string; phone:string; role:string }) =>
    adminTenantApi.createUser(id, data), [id]));
  const suspendUserAction = useAction(useCallback((userId: string) =>
    adminTenantApi.suspendUser(id, userId), [id]));
  const addAreaAction   = useAction(useCallback((data: { city:string; state:string; zipcode?:string; coverage_type:string }) =>
    adminTenantApi.createServiceArea(id, data), [id]));

  // ── Local state ────────────────────────────────────────────────────────────
  const [creditOpen,     setCreditOpen]     = useState(false);
  const [creditAmt,      setCreditAmt]      = useState("");
  const [creditNote,     setCreditNote]     = useState("");
  const [suspendOpen,    setSuspendOpen]    = useState(false);
  const [suspendMsg,     setSuspendMsg]     = useState("");
  const [planModal,      setPlanModal]      = useState(false);
  const [newPlan,        setNewPlan]        = useState("enterprise");
  const [planReason,     setPlanReason]     = useState("");
  const [reinstateOpen,  setReinstateOpen]  = useState(false);
  const [reinstateMsg,   setReinstateMsg]   = useState("");
  const [toast,          setToast]          = useState("");
  const [logoFailed,     setLogoFailed]     = useState(false);
  const [adjDepositOpen, setAdjDepositOpen] = useState(false);
  const [adjAmt,         setAdjAmt]         = useState("");
  const [adjReason,      setAdjReason]      = useState("");
  const [adjCategory,    setAdjCategory]    = useState<"goodwill"|"dispute"|"correction"|"refund">("correction");

  // Tenant 360 redesign — More Actions menu + Request Changes / Send Notification modals
  const [moreOpen,        setMoreOpen]        = useState(false);
  const [reqChangesOpen,  setReqChangesOpen]  = useState(false);
  const [reqChangesMsg,   setReqChangesMsg]   = useState("");
  const [notifyOpen,      setNotifyOpen]      = useState(false);
  const [notifySubject,   setNotifySubject]   = useState("");
  const [notifyMsg,       setNotifyMsg]       = useState("");
  const [copiedId,        setCopiedId]        = useState(false);
  // FINAL-L5-05T: after creating a service area, ProviderAreasTab must
  // refetch its own list (previously the modal called `zones.refetch()`,
  // which is the unrelated Geo Zones data source at /v1/geo/... -- newly
  // created service areas never appeared without a full page reload).
  const [areasRefreshToken, setAreasRefreshToken] = useState(0);

  const requestChangesAction = useAction(useCallback((reason: string) =>
    adminTenantsApi.requestChanges(id, reason), [id]));
  const sendNotificationAction = useAction(useCallback((subject: string, message: string) =>
    adminTenantsApi.sendNotification(id, subject, message), [id]));
  const exportAction = useAction(useCallback(() => adminTenantsApi.exportTenantReport(id), [id]));

  async function handleExportReport() {
    const blob = await exportAction.execute();
    if (blob) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `tenant_${id}_report.csv`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notify("Tenant report exported.");
    }
  }

  async function handleRequestChanges() {
    const res = await requestChangesAction.execute(reqChangesMsg);
    if (res !== null) { tenant.refetch(); setReqChangesOpen(false); setReqChangesMsg(""); notify("Change request sent to tenant."); }
  }
  async function handleSendNotification() {
    const res = await sendNotificationAction.execute(notifySubject, notifyMsg);
    if (res !== null) { setNotifyOpen(false); setNotifySubject(""); setNotifyMsg(""); notify("Notification sent."); }
  }
  function copyTenantId() {
    navigator.clipboard?.writeText(id).then(() => { setCopiedId(true); setTimeout(() => setCopiedId(false), 1500); });
  }

  // Sprint 4 — Add Staff modal state
  const [addStaffOpen,  setAddStaffOpen]  = useState(false);
  const [staffName,     setStaffName]     = useState("");
  const [staffEmail,    setStaffEmail]    = useState("");
  const [staffPhone,    setStaffPhone]    = useState("");
  // Sprint 4 — Add User modal state
  const [addUserOpen,   setAddUserOpen]   = useState(false);
  const [userName,      setUserName]      = useState("");
  const [userEmail,     setUserEmail]     = useState("");
  const [userPhone,     setUserPhone]     = useState("");
  const [userRole,      setUserRole]      = useState("tenant_manager");
  // Sprint 4 — Add Service Area modal state
  const [addAreaOpen,   setAddAreaOpen]   = useState(false);
  const [areaCity,      setAreaCity]      = useState("");
  const [areaState,     setAreaState]     = useState("");
  const [areaZipcode,   setAreaZipcode]   = useState("");
  const [areaCoverage,  setAreaCoverage]  = useState("city");

  // Serviceability test state
  const [testCity,    setTestCity]    = useState("");
  const [testZipcode, setTestZipcode] = useState("");
  const [testService, setTestService] = useState("");
  const [testJobType, setTestJobType] = useState("repair");
  const [testResult,  setTestResult]  = useState<{ check: import("../../../../lib/api").ServiceabilityCheckResponse; tenants: MatchedTenant[] } | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError,   setTestError]   = useState("");

  async function runServiceabilityTest() {
    if (!testCity.trim() || !testService.trim()) return;
    setTestLoading(true); setTestError(""); setTestResult(null);
    try {
      const body = { city: testCity, zipcode: testZipcode || undefined, service_id: testService, job_type: testJobType };
      const [check, matching] = await Promise.all([
        serviceabilityApi.check(body),
        serviceabilityApi.matchingTenants(body),
      ]);
      setTestResult({ check, tenants: matching.matched_tenants ?? [] });
    } catch (e) {
      setTestError(e instanceof Error ? e.message : "Test failed.");
    } finally {
      setTestLoading(false);
    }
  }

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const t   = tenant.data;
  const ledgerEntries = wallet.data?.entries ?? [];
  const ledgerLatestBalance = ledgerEntries[0]?.balance_after;
  const ledgerLifetimeConsumed = ledgerEntries
    .filter(e => e.credit_delta < 0)
    .reduce((sum, e) => sum + Math.abs(e.credit_delta), 0);
  const ledgerLifetimePurchased = ledgerEntries
    .filter(e => e.credit_delta > 0)
    .reduce((sum, e) => sum + e.credit_delta, 0);
  // Derived from the real usage_credit_ledger (see `wallet` hook above), not from tenant_wallets.
  const w = wallet.data ? {
    credit_balance: ledgerLatestBalance ?? 0,
    balance: ledgerLatestBalance ?? 0,
    lifetime_consumed: ledgerLifetimeConsumed,
    lifetime_purchased: ledgerLifetimePurchased,
    // No low-balance-threshold column exists on usage_credit_ledger/tenant_billing today;
    // documented heuristic only (not a backend-confirmed policy) — flagged in reports.
    low_balance_alert: (ledgerLatestBalance ?? 0) > 0 && (ledgerLatestBalance ?? 0) < 500,
  } : undefined;
  const r   = revAgg.data;
  const fmt = (n: number | undefined | null) => `₹${(n ?? 0).toLocaleString("en-IN")}`;

  async function handleCredit() {
    const res = await creditAction.execute(Number(creditAmt), creditNote);
    if (res !== null) { wallet.refetch(); txns.refetch(); setCreditOpen(false); setCreditAmt(""); setCreditNote(""); notify("Usage credits added successfully."); }
  }
  async function handleSuspend() {
    const res = await suspendAction.execute(suspendMsg);
    if (res !== null) { tenant.refetch(); setSuspendOpen(false); setSuspendMsg(""); notify("Tenant suspended."); }
  }
  async function handleReinstate() {
    const res = await reinstateAction.execute(reinstateMsg);
    if (res !== null) { tenant.refetch(); setReinstateOpen(false); setReinstateMsg(""); notify("Tenant reinstated."); }
  }
  async function handleUpgradePlan() {
    const res = await upgradePlanAction.execute(newPlan, planReason);
    if (res !== null) { tenant.refetch(); billing.refetch(); setPlanModal(false); setPlanReason(""); notify(`Plan changed to ${newPlan}.`); }
  }

  return (
    <AdminLayout activeNav="tenants">
      {/* Breadcrumb */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16, fontSize:12, color:"var(--text-tertiary)" }}>
        <a href="/admin/tenants" style={{ color:"var(--text-link)", textDecoration:"none" }}>Tenants</a>
        <span>›</span>
        <span style={{ color:"var(--text-primary)", fontWeight:500 }}>
          {tenant.loading ? "…" : t?.tenant_name ?? id}
        </span>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{ padding:"10px 16px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
          borderRadius:10, color:"var(--success-text)", fontSize:13, marginBottom:16, display:"flex", gap:8 }}>
          <span>✓</span> {toast}
        </div>
      )}

      {/* ── Hero card ─────────────────────────────────────────────────────────── */}
      {tenant.loading ? (
        <Skeleton height={220} style={{ borderRadius:20, marginBottom:24 }}/>
      ) : tenant.error ? (
        <div style={{ marginBottom:24, padding:"16px 20px", borderRadius:16,
          background:"var(--danger-bg)", border:"1px solid var(--danger-border)",
          display:"flex", alignItems:"center", gap:12 }}>
          <AlertCircle size={18} style={{ color:"var(--danger-text)", flexShrink:0 }}/>
          <span style={{ fontSize:13, color:"var(--danger-text)", flex:1 }}>Failed to load tenant: {tenant.error}</span>
          <Btn size="sm" variant="secondary" onClick={() => tenant.refetch()}>Retry</Btn>
        </div>
      ) : (
        <div style={{ marginBottom:24, borderRadius:20, overflow:"hidden",
          background:"linear-gradient(135deg, var(--surface) 0%, var(--surface-sunken) 60%)",
          border:"1px solid var(--border)", boxShadow:"0 4px 32px rgba(0,0,0,0.10)" }}>

          {/* Top accent strip */}
          <div style={{ height:4, background:"linear-gradient(90deg, var(--brand) 0%, #6366f1 50%, #8b5cf6 100%)" }}/>

          <div style={{ padding:"24px 28px" }}>
            <div style={{ display:"flex", alignItems:"flex-start", gap:22, flexWrap:"wrap" }}>

              {/* Avatar */}
              {t?.logo_url && !logoFailed ? (
                <img src={t.logo_url} alt={`${t.tenant_name} logo`}
                  style={{ width:80, height:80, borderRadius:18, objectFit:"cover",
                    border:"2px solid var(--border)", flexShrink:0, background:"var(--surface)",
                    boxShadow:"0 2px 12px rgba(0,0,0,0.12)" }}
                  onError={() => setLogoFailed(true)} />
              ) : (
                <div style={{ width:80, height:80, borderRadius:18, flexShrink:0,
                  background:"linear-gradient(135deg, var(--brand) 0%, #6366f1 100%)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  color:"white", fontWeight:800, fontSize:28,
                  boxShadow:"0 4px 16px rgba(37,99,235,0.35)" }}>
                  {t?.tenant_name?.[0]?.toUpperCase() ?? "?"}
                </div>
              )}

              {/* Identity block */}
              <div style={{ flex:"1 1 240px", minWidth:200 }}>
                <h1 style={{ fontSize:22, fontWeight:800, color:"var(--text-primary)", margin:"0 0 5px",
                  letterSpacing:"-0.01em" }}>
                  {t?.tenant_name ?? "—"}
                </h1>
                <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                  {[t?.city, t?.state].filter(Boolean).join(", ")}
                  {t?.created_at ? ` · Since ${new Date(t.created_at).toLocaleDateString("en-IN",{month:"short",year:"numeric"})}` : ""}
                </p>

                {/* Badges row */}
                <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:12 }}>
                  <Badge variant={t?.status === "active" ? "success" : t?.status === "suspended" ? "danger" : "warning"}>
                    {labelOf(t?.status)}
                  </Badge>
                  <Badge variant="info">{labelOf(t?.plan_type)}</Badge>
                  <Badge variant={t?.health_band === "gold" || t?.health_band === "platinum" ? "success" : "muted"}>
                    {labelOf(t?.health_band)}
                  </Badge>
                  <Badge variant={t?.is_discoverable !== false && t?.status === "active" ? "success" : "muted"}>
                    {t?.is_discoverable !== false && t?.status === "active" ? "Bookable" : "Not Bookable"}
                  </Badge>
                  {t?.verification_status && t.verification_status !== "approved" && (
                    <Badge variant="warning">{labelOf(t.verification_status)}</Badge>
                  )}
                </div>

                {/* Meta chips */}
                <div style={{ display:"flex", flexWrap:"wrap", gap:10, alignItems:"center" }}>
                  <button onClick={copyTenantId} style={{ display:"inline-flex", alignItems:"center", gap:5,
                    fontSize:11, fontFamily:"monospace", color:"var(--text-tertiary)",
                    background:"var(--surface-sunken)", border:"1px solid var(--border)",
                    borderRadius:8, padding:"3px 9px", cursor:"pointer" }}>
                    {copiedId ? "✓ Copied" : `ID: ${id.slice(0,8)}…`}
                  </button>
                  {billing.data?.billing_mode && (
                    <span style={{ fontSize:11, color:"var(--text-tertiary)", padding:"3px 9px",
                      background:"var(--surface-sunken)", borderRadius:8, border:"1px solid var(--border)" }}>
                      {labelOf(billing.data.billing_mode)}
                    </span>
                  )}
                  {billing.data?.commission_rate != null && (
                    <span style={{ fontSize:11, color:"var(--text-tertiary)", padding:"3px 9px",
                      background:"var(--surface-sunken)", borderRadius:8, border:"1px solid var(--border)" }}>
                      Commission: {(billing.data.commission_rate * 100).toFixed(1)}%
                    </span>
                  )}
                  {t?.health_score != null && (
                    <span style={{ fontSize:11, fontWeight:700,
                      color: t.health_score >= 70 ? "var(--success-text)" : t.health_score >= 40 ? "var(--warning-text)" : "var(--danger-text)",
                      padding:"3px 9px", borderRadius:8, border:"1px solid var(--border)",
                      background:"var(--surface-sunken)" }}>
                      Health: {Math.round(t.health_score)}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display:"flex", flexDirection:"column", gap:8, alignItems:"flex-end" }}>
                <div style={{ display:"flex", gap:8, flexWrap:"wrap", justifyContent:"flex-end", position:"relative" }}>
                  {/* FINAL-L5-05P: Change Plan/Suspend/Reinstate all call
                      backend endpoints gated by require_super_admin (not
                      yet granular) -- gated by role, not page-read
                      permission alone. Add Usage Credits is Finance-domain,
                      out of this sprint's bounded scope, left unchanged. */}
                  {!isMobile && <>
                    <Btn size="sm" icon={<CreditCard size={13}/>} onClick={() => setCreditOpen(true)}>
                      Add Usage Credits
                    </Btn>
                    {perm.role === "super_admin" && (
                      <Btn variant="secondary" size="sm" onClick={() => setPlanModal(true)}>Change Plan</Btn>
                    )}
                    {perm.role === "super_admin" && t?.status && !["suspended","terminated","archived"].includes(t.status) && (
                      <Btn variant="danger" size="sm" loading={suspendAction.loading} onClick={() => setSuspendOpen(true)}>
                        Suspend
                      </Btn>
                    )}
                    {perm.role === "super_admin" && t?.status === "suspended" && (
                      <Btn variant="success" size="sm" loading={reinstateAction.loading} onClick={() => setReinstateOpen(true)}>
                        Reinstate
                      </Btn>
                    )}
                  </>}
                  <div style={{ position:"relative" }}>
                    <Btn variant="secondary" size="sm" onClick={() => setMoreOpen(o => !o)}>More ⋯</Btn>
                    {moreOpen && (
                      <div style={{ position:"absolute", top:"100%", right:0, marginTop:6, zIndex:30,
                        background:"var(--surface)", border:"1px solid var(--border)", borderRadius:12,
                        boxShadow:"0 12px 40px rgba(0,0,0,0.18)", minWidth:210, overflow:"hidden" }}>
                        {isMobile && <>
                          <button onClick={() => { setMoreOpen(false); setCreditOpen(true); }} style={menuItemStyle}>Add Usage Credits</button>
                          {perm.role === "super_admin" && (
                            <button onClick={() => { setMoreOpen(false); setPlanModal(true); }} style={menuItemStyle}>Change Plan</button>
                          )}
                          {perm.role === "super_admin" && t?.status && !["suspended","terminated","archived"].includes(t.status) && (
                            <button onClick={() => { setMoreOpen(false); setSuspendOpen(true); }} style={menuItemStyle}>Suspend</button>
                          )}
                          {perm.role === "super_admin" && t?.status === "suspended" && (
                            <button onClick={() => { setMoreOpen(false); setReinstateOpen(true); }} style={menuItemStyle}>Reinstate</button>
                          )}
                          <hr style={{ margin:"4px 0", border:"none", borderTop:"1px solid var(--border)" }}/>
                        </>}
                        <button onClick={() => { setMoreOpen(false); setTab("onboarding"); }} style={menuItemStyle}>Approve / Review Tenant</button>
                        <button onClick={() => { setMoreOpen(false); setAdjDepositOpen(true); }} style={menuItemStyle}>Adjust Security Deposit</button>
                        {perm.role === "super_admin" && (
                          <button onClick={() => { setMoreOpen(false); setReqChangesOpen(true); }} style={menuItemStyle}>Request Changes</button>
                        )}
                        {perm.role === "super_admin" && (
                          <button onClick={() => { setMoreOpen(false); setNotifyOpen(true); }} style={menuItemStyle}>Send Notification</button>
                        )}
                        <hr style={{ margin:"4px 0", border:"none", borderTop:"1px solid var(--border)" }}/>
                        {perm.role === "super_admin" && (
                          <button onClick={() => { setMoreOpen(false); handleExportReport(); }} style={menuItemStyle}>
                            {exportAction.loading ? "Exporting…" : "Export Tenant Report"}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Usage Credits mini card */}
                <div style={{ padding:"10px 16px", borderRadius:12, border:"1px solid var(--border)",
                  background:"var(--surface-sunken)", textAlign:"center", minWidth:140 }}>
                  <p style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                    color:"var(--text-tertiary)", margin:"0 0 3px" }}>Usage Credits</p>
                  <p style={{ fontSize:18, fontWeight:800, color:"var(--text-primary)", margin:"0 0 4px" }}>
                    {fmt(w?.credit_balance ?? w?.balance ?? 0)}
                  </p>
                  <button onClick={() => setCreditOpen(true)}
                    style={{ fontSize:11, fontWeight:600, color:"var(--brand)",
                      background:"none", border:"none", cursor:"pointer", padding:0 }}>
                    + Add
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* ── KPI grid (8 cards) ────────────────────────────────────────────────── */}
      <div style={{ display:"grid", gridTemplateColumns:`repeat(${kpiCols},1fr)`, gap:20, marginBottom:24 }}>
        {(tenant.loading || wallet.loading) ? (
          [...Array(8)].map((_,i) => <Skeleton key={i} height={120} style={{ borderRadius:14 }}/>)
        ) : <>
          <StatCard label="Usage Credit Balance" value={fmt(w?.credit_balance ?? w?.balance ?? 0)} icon={<CreditCard/>}
            trend={w?.low_balance_alert ? "down" : "neutral"} alert={!!w?.low_balance_alert}/>
          <StatCard label="Credits Deducted Lifetime" value={fmt(w?.lifetime_consumed ?? 0)} icon={<CheckCircle2/>}
            trend="neutral" alert={false}/>
          <StatCard label="Security Deposit Held" value={fmt(deposit.data?.current_balance ?? 0)} icon={<ShieldOff/>}
            trend="neutral" alert={(deposit.data?.current_balance ?? 0) === 0}/>
          <StatCard label="Health Score" value={Math.round(t?.health_score ?? 0)} icon={<Zap/>} trend="neutral"/>
          <StatCard label="Staff Members" value={(staff.data?.users ?? []).length} icon={<Users/>} trend="neutral"/>
          <StatCard label="Average Rating" value={r?.avg_composite?.toFixed(1) ?? "—"} icon={<Star/>} trend="neutral"/>
          <StatCard label="Open Complaints" value={(penalties.data?.penalties ?? []).filter(p => !["resolved","closed","settled","reversed"].includes(p.status ?? "")).length}
            icon={<AlertCircle/>} trend="neutral" alert={(penalties.data?.penalties ?? []).length > 0}/>
          <StatCard label="Active Jobs" value={(allJobs.data?.items ?? []).filter(j => !["completed","cancelled"].includes(j.status)).length}
            icon={<Briefcase/>} trend="neutral"/>
        </>}
      </div>

      {/* ── Grouped tabs ──────────────────────────────────────────────────────── */}
      {isMobile ? (
        // Mobile: segmented dropdowns instead of two tab rows (spec: "Tabs become segmented dropdown")
        <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:20 }}>
          <select value={groupForTab(tab).key} onChange={e => {
            const g = TAB_GROUPS.find(x => x.key === e.target.value);
            if (g) setTab(g.tabs[0]);
          }} style={selectStyle}>
            {TAB_GROUPS.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
          </select>
          <select value={tab} onChange={e => setTab(e.target.value as Tab)} style={selectStyle}>
            {TABS.filter(tb => groupForTab(tab).tabs.includes(tb.id)).map(tb => (
              <option key={tb.id} value={tb.id}>{tb.label}</option>
            ))}
          </select>
        </div>
      ) : (
        <>
          <div style={{ display:"flex", gap:6, marginBottom:10, flexWrap:"wrap" }}>
            {TAB_GROUPS.map(g => {
              const active = groupForTab(tab).key === g.key;
              return (
                <button key={g.key} onClick={() => setTab(g.tabs[0])}
                  style={{ padding:"8px 16px", borderRadius:999, cursor:"pointer", fontSize:13,
                    fontWeight: active ? 700 : 500,
                    border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
                    background: active ? "var(--brand)" : "var(--surface)",
                    color: active ? "white" : "var(--text-secondary)" }}>
                  {g.label}
                </button>
              );
            })}
          </div>
          <div style={{ display:"flex", gap:2, borderBottom:"2px solid var(--border)", marginBottom:20, overflowX:"auto" }}>
            {TABS.filter(tb => groupForTab(tab).tabs.includes(tb.id)).map(tb => (
              <button key={tb.id} onClick={() => setTab(tb.id)}
                style={{ padding:"10px 16px", border:"none", background:"none", cursor:"pointer",
                  fontSize:13, fontWeight:tab === tb.id ? 700 : 500,
                  color: tab === tb.id ? "var(--brand)" : "var(--text-secondary)",
                  borderBottom: tab === tb.id ? "2px solid var(--brand)" : "2px solid transparent",
                  marginBottom:-2, whiteSpace:"nowrap", display:"flex", gap:6, alignItems:"center" }}>
                <span style={{ display:"flex", alignItems:"center" }}>
                  {React.isValidElement(tb.icon)
                    ? React.cloneElement(tb.icon as React.ReactElement<{ size?: number }>, { size: 14 })
                    : tb.icon}
                </span> {tb.label}
              </button>
            ))}
          </div>
        </>
      )}

      {/* ════════════════════ OVERVIEW ════════════════════ */}
      {tab === "overview" && (() => {
        const checks: { label: string; ok: boolean; jumpTab?: Tab }[] = [
          { label: "Business Profile Complete", ok: !!(t?.tenant_name && t?.city && t?.state), jumpTab: "onboarding" },
          { label: "Owner Verified",            ok: t?.status === "active" || t?.status === "suspended", jumpTab: "onboarding" },
          { label: "Service Areas Configured",  ok: (zones.data?.zones ?? []).length > 0, jumpTab: "service-areas" },
          { label: "Services Enabled",          ok: (enabledSvcs.data?.services ?? []).length > 0, jumpTab: "enabled-services" },
          { label: "Pricing Configured",        ok: (pricing.data?.rules ?? []).length > 0, jumpTab: "pricing" },
          { label: "Staff Added",               ok: (staff.data?.users ?? []).length > 0, jumpTab: "staff" },
          { label: "Package Active",            ok: !!((packages.data as unknown as { packages?: { is_active?: boolean }[] })?.packages ?? []).some(p => p.is_active), jumpTab: "packages" },
          { label: "Usage Credits Available",   ok: (w?.credit_balance ?? w?.balance ?? 0) > 0, jumpTab: "wallet" },
          { label: "Security Deposit Held",     ok: (deposit.data?.current_balance ?? 0) > 0, jumpTab: "deposit" },
          { label: "Bookable Status Enabled",   ok: t?.status === "active" && t?.is_discoverable !== false, jumpTab: "bookability" },
        ];
        const passCount = checks.filter(c => c.ok).length;
        const pct = Math.round((passCount / checks.length) * 100);
        const overall = passCount === checks.length ? "Ready" : passCount >= checks.length * 0.7 ? "Needs Setup" : passCount >= checks.length * 0.4 ? "At Risk" : "Blocked";
        const ringColor = overall === "Ready" ? "var(--success)" : overall === "Blocked" ? "var(--danger)" : "var(--warning)";
        const overallVariant: "success"|"warning"|"danger" = overall === "Ready" ? "success" : overall === "Blocked" ? "danger" : "warning";

        // Health signals for right panel
        const PRIORITY_SIGNALS = ["job_completion","customer_satisfaction","warranty_claim_rate","warranty_claim","credit_wallet_health","usage_credit_health"];
        const allSignals = Object.entries(health.data?.signals ?? {});
        const orderedSignals = [
          ...PRIORITY_SIGNALS.flatMap(k => allSignals.filter(([key]) => key === k)),
          ...allSignals.filter(([key]) => !PRIORITY_SIGNALS.includes(key)),
        ].slice(0, 4);

        return (
          <div style={{ display:"grid", gridTemplateColumns:overviewCols, gap:16 }}>
            {/* ── LEFT COLUMN ── */}
            <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

              {/* Provider Readiness */}
              <Card padding={24}>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:18 }}>
                  <h3 style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:0 }}>Provider Readiness</h3>
                  <Badge variant={overallVariant}>{overall}</Badge>
                </div>
                <div style={{ display:"flex", gap:20, alignItems:"flex-start", marginBottom:18 }}>
                  <CircularProgress pct={pct} size={88} color={ringColor}/>
                  <div>
                    <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 4px" }}>
                      {passCount} of {checks.length} checks complete
                    </p>
                    <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                      {overall === "Ready" ? "Provider is fully set up and bookable." :
                       overall === "Blocked" ? "Critical items missing — provider is not bookable." :
                       "Some setup items still pending."}
                    </p>
                  </div>
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                  {checks.map(c => {
                    const content = (
                      <div style={{ display:"flex", alignItems:"center", gap:7, fontSize:12,
                        padding:"5px 8px", borderRadius:8,
                        background: c.ok ? "var(--success-bg)" : "var(--danger-bg)",
                        border:`1px solid ${c.ok ? "var(--success-border)" : "var(--danger-border)"}` }}>
                        {c.ok
                          ? <CheckCircle2 size={13} style={{ color:"var(--success-text)", flexShrink:0 }}/>
                          : <AlertCircle size={13} style={{ color:"var(--danger-text)", flexShrink:0 }}/>}
                        <span style={{ color: c.ok ? "var(--success-text)" : "var(--danger-text)", fontWeight: c.ok ? 500 : 600, lineHeight:1.3 }}>
                          {c.label}
                        </span>
                      </div>
                    );
                    return c.ok || !c.jumpTab ? (
                      <div key={c.label}>{content}</div>
                    ) : (
                      <button key={c.label} onClick={() => setTab(c.jumpTab as Tab)}
                        style={{ border:"none", background:"none", padding:0, cursor:"pointer", textAlign:"left" }}>
                        {content}
                      </button>
                    );
                  })}
                </div>
              </Card>

              {/* Recent Jobs */}
              <Card padding={0}>
                <div style={{ padding:"13px 18px", borderBottom:"1px solid var(--border)",
                  display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0,
                    display:"flex", alignItems:"center", gap:6 }}>
                    <Briefcase size={14}/> Recent Jobs
                  </h3>
                  <button onClick={() => setTab("jobs")} style={{ fontSize:12, color:"var(--text-link)",
                    background:"none", border:"none", cursor:"pointer" }}>All jobs →</button>
                </div>
                {recentJobs.loading ? (
                  <div style={{ padding:"12px 18px", display:"flex", flexDirection:"column", gap:8 }}>
                    {[...Array(3)].map((_,i) => <Skeleton key={i} height={36}/>)}
                  </div>
                ) : (recentJobs.data?.items ?? []).length === 0 ? (
                  <p style={{ padding:"28px 18px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                    No recent jobs
                  </p>
                ) : (recentJobs.data?.items ?? []).map((j, i, arr) => (
                  <div key={j.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 18px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div style={{ flex:1, minWidth:0 }}>
                      <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                        {j.job_number} · {j.city ?? "—"}
                      </p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                        {j.assigned_staff_id ? "Assigned" : "Unassigned"}
                      </p>
                    </div>
                    <JobStatusBadge status={j.status}/>
                  </div>
                ))}
              </Card>

              {/* Recent Bookings */}
              <Card padding={0}>
                <div style={{ padding:"13px 18px", borderBottom:"1px solid var(--border)",
                  display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0,
                    display:"flex", alignItems:"center", gap:6 }}>
                    <CalendarCheck size={14}/> Recent Bookings
                  </h3>
                  <button onClick={() => setTab("bookings")} style={{ fontSize:12, color:"var(--text-link)",
                    background:"none", border:"none", cursor:"pointer" }}>All bookings →</button>
                </div>
                {recentBkgs.loading ? (
                  <div style={{ padding:"12px 18px", display:"flex", flexDirection:"column", gap:8 }}>
                    {[...Array(3)].map((_,i) => <Skeleton key={i} height={36}/>)}
                  </div>
                ) : (recentBkgs.data?.bookings ?? []).length === 0 ? (
                  <p style={{ padding:"28px 18px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                    No bookings yet
                  </p>
                ) : (recentBkgs.data?.bookings ?? []).map((bk: Booking, i, arr) => (
                  <div key={bk.booking_id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 18px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div style={{ flex:1, minWidth:0 }}>
                      <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                        {bk.booking_number} · {bk.service_type_id ?? "—"}
                      </p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                        {new Date(bk.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
                        {bk.preferred_date && ` · ${bk.preferred_date}`}
                      </p>
                    </div>
                    <Badge variant={BOOKING_VARIANT[bk.status] ?? "muted"} size="sm">
                      {bk.status.replace(/_/g," ")}
                    </Badge>
                  </div>
                ))}
              </Card>

              {/* Enabled Engines */}
              <EffectiveEnginesCard tenantId={id} />

            </div>

            {/* ── RIGHT COLUMN ── */}
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

              {/* Reviews */}
              <Card padding={20}>
                <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                  color:"var(--text-tertiary)", margin:"0 0 14px" }}>Reviews</p>
                {revAgg.loading ? <Skeleton height={56}/> : (
                  <div style={{ display:"flex", alignItems:"center", gap:14 }}>
                    <div style={{ textAlign:"center" }}>
                      <p style={{ fontSize:36, fontWeight:800, color:"var(--text-primary)", margin:0, lineHeight:1 }}>
                        {r?.avg_composite?.toFixed(1) ?? "—"}
                      </p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"3px 0 0" }}>avg rating</p>
                    </div>
                    <div style={{ flex:1 }}>
                      <p style={{ fontSize:14, color:"var(--text-secondary)", margin:"0 0 2px", fontWeight:600 }}>
                        {r?.review_count ?? 0} reviews
                      </p>
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                        {(r?.review_count ?? 0) === 0 ? "No ratings yet" : `Reply rate: ${r?.reply_rate ?? 0}%`}
                      </p>
                    </div>
                  </div>
                )}
              </Card>

              {/* Tenant Info */}
              <Card padding={20}>
                <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                  color:"var(--text-tertiary)", margin:"0 0 12px" }}>Tenant Info</p>
                {[
                  { label:"Billing Mode", v: labelOf(billing.data?.billing_mode) },
                  { label:"Commission",   v: billing.data ? `${(billing.data.commission_rate * 100).toFixed(1)}%` : "—" },
                  { label:"Health Band",  v: labelOf(t?.health_band) },
                  { label:"Activated",    v: t?.activated_at ? new Date(t.activated_at).toLocaleDateString("en-IN") : "—" },
                  { label:"Tenant ID",    v: id.slice(0,8), mono: true },
                ].map(row => (
                  <div key={row.label} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"6px 0", borderBottom:"1px solid var(--border)" }}>
                    <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{row.label}</span>
                    <span style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)",
                      fontFamily: row.mono ? "monospace" : undefined }}>
                      {row.v}
                    </span>
                  </div>
                ))}
              </Card>

              {/* Health Signals */}
              <Card padding={18}>
                <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                  color:"var(--text-tertiary)", margin:"0 0 12px" }}>Health Signals</p>
                {health.loading ? <Skeleton height={80}/> :
                 orderedSignals.length === 0 ? (
                   <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>No health data yet</p>
                 ) : orderedSignals.map(([sig, rawScore]) => {
                  const score = Number(rawScore) || 0;
                  const label = SIGNAL_LABELS[sig] ?? sig.replace(/_/g," ").replace(/\b\w/g, c => c.toUpperCase());
                  return (
                    <div key={sig} style={{ marginBottom:10 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                        <span style={{ fontSize:11, color:"var(--text-secondary)" }}>{label}</span>
                        <span style={{ fontSize:11, fontWeight:700,
                          color: score >= 70 ? "var(--success-text)" : score >= 40 ? "var(--warning-text)" : "var(--danger-text)" }}>
                          {Math.round(score)}%
                        </span>
                      </div>
                      <div style={{ height:5, background:"var(--border)", borderRadius:999, overflow:"hidden" }}>
                        <div style={{ height:"100%", width:`${Math.min(score, 100)}%`, borderRadius:999,
                          background: score >= 70 ? "var(--success)" : score >= 40 ? "var(--warning)" : "var(--danger)",
                          transition:"width 0.4s ease" }}/>
                      </div>
                    </div>
                  );
                })}
              </Card>

              {/* Feature flags (compact) */}
              {flags.data && Object.keys(flags.data.flags ?? {}).length > 0 && (
                <Card padding={16}>
                  <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                    color:"var(--text-tertiary)", margin:"0 0 10px" }}>Feature Flags</p>
                  <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                    {Object.entries(flags.data.flags ?? {}).map(([key, flag]) => (
                      <span key={key} style={{ fontSize:10, fontFamily:"monospace", padding:"2px 7px",
                        borderRadius:6, border:"1px solid var(--border)",
                        background: flag.value === true ? "var(--success-bg)" : flag.value === false ? "var(--danger-bg)" : "var(--surface-sunken)",
                        color: flag.value === true ? "var(--success-text)" : flag.value === false ? "var(--danger-text)" : "var(--text-secondary)" }}>
                        {key}={String(flag.value)}
                      </span>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          </div>
        );
      })()}

      {/* ════════════════════ STAFF ════════════════════ */}
      {tab === "staff" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              {staff.data ? `${(staff.data.users ?? []).length} staff member${(staff.data.users ?? []).length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
            <div style={{ display:"flex", gap:8 }}>
              {perm.role === "super_admin" && (
                <Btn size="sm" onClick={() => setAddStaffOpen(true)}>+ Add Staff</Btn>
              )}
              <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => staff.refetch()}>Refresh</Btn>
            </div>
          </div>
          <Card padding={0}>
            {staff.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(5)].map((_,i) => <Skeleton key={i} height={60}/>)}
              </div>
            ) : (staff.data?.users ?? []).length === 0 ? (
              <div style={{ padding:"48px 20px", textAlign:"center" }}>
                <div style={{ marginBottom:12 }}><Users size={32} style={{ color:"var(--text-tertiary)" }}/></div>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No staff found for this tenant</p>
              </div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Name / Email","Role","Status","Verified","Last Login","Actions"].map(h => (
                      <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                        color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(staff.data?.users ?? []).map((s: AdminStaffUser, i, arr) => (
                    <tr key={s.user_id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"12px 16px" }}>
                        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                          <div style={{ width:34, height:34, borderRadius:"50%", flexShrink:0,
                            background:"var(--accent-muted)", display:"flex", alignItems:"center",
                            justifyContent:"center", fontWeight:700, fontSize:14, color:"var(--accent)" }}>
                            {s.full_name?.[0]?.toUpperCase() ?? "?"}
                          </div>
                          <div>
                            <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{s.full_name}</p>
                            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{s.email}</p>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding:"12px 16px" }}>
                        <Badge variant="muted" size="sm">{s.role}</Badge>
                      </td>
                      <td style={{ padding:"12px 16px" }}>
                        <Badge variant={s.is_active ? "success" : "danger"} size="sm">
                          {s.is_active ? "Active" : "Deactivated"}
                        </Badge>
                      </td>
                      <td style={{ padding:"12px 16px" }}>
                        {s.is_verified
                          ? <Badge variant="success" size="sm">Verified</Badge>
                          : <Badge variant="warning" size="sm">Pending</Badge>}
                      </td>
                      <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                        {s.last_login_at ? new Date(s.last_login_at).toLocaleDateString("en-IN") : "Never"}
                      </td>
                      <td style={{ padding:"12px 16px" }}>
                        {perm.role === "super_admin" && s.is_active && (
                          <Btn size="xs" variant="danger"
                            loading={deactivateStaffAction.loading}
                            onClick={async () => {
                              const res = await deactivateStaffAction.execute(s.user_id);
                              if (res !== null) { staff.refetch(); notify("Staff deactivated."); }
                            }}>
                            Deactivate
                          </Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ USERS ════════════════════ */}
      {tab === "users" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              {users.data ? `${(users.data.users ?? []).length} user${(users.data.users ?? []).length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
            <div style={{ display:"flex", gap:8 }}>
              {perm.role === "super_admin" && (
                <Btn size="sm" onClick={() => setAddUserOpen(true)}>+ Add User</Btn>
              )}
              <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => users.refetch()}>Refresh</Btn>
            </div>
          </div>
          <Card padding={0}>
            {users.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height={52}/>)}
              </div>
            ) : (users.data?.users ?? []).length === 0 ? (
              <div style={{ padding:"48px 20px", textAlign:"center" }}>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No users found for this tenant</p>
              </div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Name","Email","Role","Status","Verified","Last Login","Actions"].map(h => (
                      <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11,
                        fontWeight:700, color:"var(--text-tertiary)", textTransform:"uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(users.data?.users ?? []).map((u, i, arr) => (
                    <tr key={String(u.user_id ?? u.id)} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"11px 16px", fontWeight:600, fontSize:13, color:"var(--text-primary)" }}>
                        {String(u.full_name ?? "—")}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:13, color:"var(--text-secondary)" }}>{String(u.email ?? "—")}</td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant="muted" size="sm">{String(u.role ?? "—")}</Badge>
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant={u.is_active ? "success" : "danger"} size="sm">
                          {u.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        {u.is_verified
                          ? <Badge variant="success" size="sm">Yes</Badge>
                          : <Badge variant="warning" size="sm">No</Badge>}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                        {u.last_login_at ? new Date(String(u.last_login_at)).toLocaleDateString("en-IN") : "Never"}
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        {perm.role === "super_admin" && u.is_active && (
                          <Btn size="xs" variant="danger"
                            loading={suspendUserAction.loading}
                            onClick={async () => {
                              const res = await suspendUserAction.execute(String(u.user_id ?? u.id));
                              if (res !== null) { users.refetch(); notify("User suspended."); }
                            }}>
                            Suspend
                          </Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ SERVICE AREAS ════════════════════ */}
      {tab === "service-areas" && (
        <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
                {zones.data ? `${(zones.data.zones ?? []).length} service zone${(zones.data.zones ?? []).length !== 1 ? "s" : ""}` : "Loading…"}
              </p>
              <div style={{ display:"flex", gap:8 }}>
                {perm.role === "super_admin" && (
                  <Btn size="sm" onClick={() => setAddAreaOpen(true)}>+ Add Area</Btn>
                )}
                <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => zones.refetch()}>Refresh</Btn>
              </div>
            </div>
            <Card padding={0}>
              {zones.loading ? (
                <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                  {[...Array(3)].map((_,i) => <Skeleton key={i} height={56}/>)}
                </div>
              ) : (zones.data?.zones ?? []).length === 0 ? (
                <div style={{ padding:"48px 20px", textAlign:"center" }}>
                  <div style={{ marginBottom:12 }}><MapPin size={32} style={{ color:"var(--text-tertiary)" }}/></div>
                  <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No service zones configured for this tenant</p>
                </div>
              ) : (
                <table style={{ width:"100%", borderCollapse:"collapse" }}>
                  <thead>
                    <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                      {["Zone Name","Type","Coverage","Surcharge","Status","Valid From"].map(h => (
                        <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                          color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(zones.data?.zones ?? []).map((z: GeoZone, i, arr) => (
                      <tr key={z.zone_id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding:"11px 16px", fontWeight:600, fontSize:13, color:"var(--text-primary)" }}>
                          {z.zone_name}
                        </td>
                        <td style={{ padding:"11px 16px" }}><Badge variant="muted">{z.zone_type}</Badge></td>
                        <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                          {z.zone_type === "radius" && z.radius_km ? `${z.radius_km} km radius` : ""}
                          {z.zone_type === "pincode" && z.identifiers.length > 0
                            ? `${z.identifiers.slice(0,3).join(", ")}${z.identifiers.length > 3 ? ` +${z.identifiers.length - 3} more` : ""}`
                            : ""}
                          {z.zone_type === "city" && z.identifiers.length > 0
                            ? z.identifiers.join(", ")
                            : ""}
                        </td>
                        <td style={{ padding:"11px 16px", fontSize:13 }}>
                          {z.surcharge_pct > 0 ? `+${z.surcharge_pct}%` : "—"}
                        </td>
                        <td style={{ padding:"11px 16px" }}>
                          <Badge variant={z.is_active ? "success" : "muted"}>{z.is_active ? "Active" : "Inactive"}</Badge>
                        </td>
                        <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                          {new Date(z.valid_from).toLocaleDateString("en-IN", { day:"numeric", month:"short", year:"numeric" })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>

          {/* Serviceability test tool */}
          <div>
            <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 10px" }}>
              Serviceability Test Tool
            </p>
            <Card padding={16}>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr auto", gap:10, alignItems:"end" }}>
                <Input label="City" placeholder="Ludhiana" value={testCity} onChange={setTestCity}/>
                <Input label="Zipcode" placeholder="141001" value={testZipcode} onChange={setTestZipcode}/>
                <Input label="Service ID" placeholder="uuid" value={testService} onChange={setTestService}/>
                <div>
                  <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
                    Job Type
                  </label>
                  <select value={testJobType} onChange={e => setTestJobType(e.target.value)}
                    style={{ width:"100%", height:38, padding:"0 10px", fontSize:13,
                      background:"var(--surface)", border:"1px solid var(--border)",
                      borderRadius:8, color:"var(--text-primary)", outline:"none" }}>
                    {["repair","service","consultation"].map(j => <option key={j} value={j}>{j}</option>)}
                  </select>
                </div>
                <Btn variant="primary" size="sm" loading={testLoading} onClick={runServiceabilityTest}>
                  Run Test
                </Btn>
              </div>
              {testError && (
                <div style={{ marginTop:14, padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
                  <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{testError}</p>
                </div>
              )}
              {testResult && (
                <div style={{ marginTop:16, display:"flex", flexDirection:"column", gap:12 }}>
                  <div style={{ padding:"12px 16px", borderRadius:10,
                    background: testResult.check.service_available ? "var(--success-bg)" : "var(--danger-bg)",
                    border: `1px solid ${testResult.check.service_available ? "var(--success-border)" : "var(--danger-border)"}` }}>
                    <p style={{ fontSize:13, fontWeight:600,
                      color: testResult.check.service_available ? "var(--success-text)" : "var(--danger-text)", margin:0 }}>
                      {testResult.check.service_available ? "✓ Available" : "✗ Not available"} — {testResult.check.message}
                    </p>
                    <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"6px 0 0" }}>
                      Best match: <strong>{testResult.check.best_match_level ?? "none"}</strong> ·
                      {" "}{testResult.check.matched_tenants_count} tenant(s)
                    </p>
                  </div>
                  {testResult.tenants.length > 0 && (
                    <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                      {testResult.tenants.map(mt => (
                        <div key={mt.tenant_id} style={{ display:"flex", justifyContent:"space-between",
                          alignItems:"center", padding:"10px 14px", borderRadius:9,
                          background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
                          <div>
                            <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                              {mt.tenant_name}
                            </p>
                            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                              Matched via <strong>{mt.coverage_match_level}</strong>
                              {mt.health_score != null && ` · health ${mt.health_score}`}
                            </p>
                          </div>
                          {mt.base_price != null && (
                            <p style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                              ₹{mt.base_price.toLocaleString("en-IN")}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* ════════════════════ MODULES & CATEGORIES (FINAL-L5-04B) ════════════════════ */}
      {tab === "entitlements" && <EntitlementsTab tenantId={id}/>}

      {/* ════════════════════ ENABLED SERVICES ════════════════════ */}
      {tab === "enabled-services" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              {enabledSvcs.data ? `${(enabledSvcs.data.services ?? []).length} enabled service${(enabledSvcs.data.services ?? []).length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
            <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => enabledSvcs.refetch()}>Refresh</Btn>
          </div>
          <Card padding={0}>
            {enabledSvcs.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(5)].map((_,i) => <Skeleton key={i} height={52}/>)}
              </div>
            ) : (enabledSvcs.data?.services ?? []).length === 0 ? (
              <div style={{ padding:"48px 20px", textAlign:"center" }}>
                <div style={{ marginBottom:12 }}><Zap size={32} style={{ color:"var(--text-tertiary)" }}/></div>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No services enabled yet</p>
                <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"6px 0 0" }}>
                  Tenant can enable services from their portal catalog.
                </p>
              </div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Display Name","Job Type","Custom Base Price","Visit Fee","Override","Status"].map(h => (
                      <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                        color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(enabledSvcs.data?.services ?? []).map((svc: EnabledService, i, arr) => (
                    <tr key={svc.tenant_service_id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"11px 16px", fontWeight:600, fontSize:13, color:"var(--text-primary)" }}>
                        {svc.tenant_display_name ?? svc.master_service_id.slice(0,8) + "…"}
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant="info" size="sm">{svc.job_type}</Badge>
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                        {svc.tenant_base_price != null ? fmt(svc.tenant_base_price) : "—"}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:13, color:"var(--text-secondary)" }}>
                        {svc.tenant_visit_fee != null ? fmt(svc.tenant_visit_fee) : "—"}
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant={svc.override_allowed ? "success" : "muted"} size="sm">
                          {svc.override_allowed ? "Allowed" : "Fixed"}
                        </Badge>
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant={svc.is_enabled && svc.is_active ? "success" : "muted"} size="sm">
                          {svc.is_enabled && svc.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ PRICING ════════════════════ */}
      {tab === "pricing" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
              Platform pricing rules — shown for reference. Tenant-specific overrides are set in Enabled Services.
            </p>
            <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => pricing.refetch()}>Refresh</Btn>
          </div>
          <Card padding={0}>
            {pricing.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(6)].map((_,i) => <Skeleton key={i} height={48}/>)}
              </div>
            ) : (pricing.data?.rules ?? []).length === 0 ? (
              <div style={{ padding:"48px 20px", textAlign:"center" }}>
                <div style={{ marginBottom:12 }}><Tag size={32} style={{ color:"var(--text-tertiary)" }}/></div>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No pricing rules found</p>
              </div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Job Type","Model","Base Price","Min–Max","Tier","Status"].map(h => (
                      <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                        color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(pricing.data?.rules ?? []).map((rule, i, arr) => (
                    <tr key={rule.rule_id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant="info" size="sm">{rule.job_type}</Badge>
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                        {rule.pricing_model?.replace(/_/g," ")}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:13, fontWeight:700, color:"var(--text-primary)" }}>
                        {fmt(rule.base_price)}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                        {rule.min_price != null ? fmt(rule.min_price) : "—"}
                        {rule.max_price != null ? ` – ${fmt(rule.max_price)}` : ""}
                      </td>
                      <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-tertiary)" }}>
                        {rule.tier_id ? rule.tier_id.slice(0,8) + "…" : "Any"}
                      </td>
                      <td style={{ padding:"11px 16px" }}>
                        <Badge variant={rule.is_active ? "success" : "muted"} size="sm">
                          {rule.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ PACKAGES & USAGE CREDITS ════════════════════ */}
      {tab === "packages" && (
        <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
          {/* Credit packages */}
          <Card padding={18}>
            <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 12px" }}>Credit Packages</p>
            {packages.loading ? <Skeleton height={80}/> : (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {((packages.data as unknown as { packages?: { id:string; name:string; credits:number; price:number; is_active:boolean }[] })?.packages ?? []).length === 0
                  ? <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No credit packages configured.</p>
                  : ((packages.data as unknown as { packages: { id:string; name:string; credits:number; price:number; is_active:boolean }[] }).packages ?? []).map(pkg => (
                    <div key={pkg.id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                      padding:"12px 16px", border:"1px solid var(--border)", borderRadius:10 }}>
                      <div>
                        <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>{pkg.name}</p>
                        <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                          ₹{(pkg.credits ?? 0).toLocaleString("en-IN")} credits
                        </p>
                      </div>
                      <div style={{ textAlign:"right" }}>
                        <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 2px" }}>
                          ₹{(pkg.price ?? 0).toLocaleString("en-IN")}
                        </p>
                        <Badge variant={pkg.is_active ? "success" : "muted"} size="sm">{pkg.is_active ? "Active" : "Inactive"}</Badge>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ SECURITY DEPOSIT ════════════════════ */}
      {tab === "deposit" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"10px 14px", background:"var(--warning-bg)", border:"1px solid var(--warning-border)", borderRadius:8 }}>
            <p style={{ fontSize:12, color:"var(--warning-text)", margin:0 }}>
              Security deposit is a one-time guarantee held separately from usage credits. It is used to cover risk (disputes, damages)
              and is only deducted with an admin reason and audit trail — it is never used for routine job-credit deductions.
            </p>
          </div>
          <Card padding={18}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:0 }}>Security Deposit Held</p>
              <Btn size="sm" variant="ghost" onClick={() => setAdjDepositOpen(true)}>Adjust Deposit</Btn>
            </div>
            {deposit.loading ? <Skeleton height={56}/> : deposit.data ? (
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:12 }}>
                {[
                  ["Status",   deposit.data.status],
                  ["Required", fmt(deposit.data.required_amount)],
                  ["Held / Available", fmt(deposit.data.current_balance)],
                ].map(([label, val]) => (
                  <div key={label} style={{ textAlign:"center", padding:"12px 0",
                    border:"1px solid var(--border)", borderRadius:10 }}>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px", textTransform:"uppercase" }}>{label}</p>
                    <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{val}</p>
                  </div>
                ))}
              </div>
            ) : <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No deposit record found.</p>}
            {(depositTxns.data as unknown as { transactions?: { txn_id:string; txn_type:string; amount:number; notes?:string; created_at:string }[] })?.transactions && (
              <div style={{ marginTop:14, borderTop:"1px solid var(--border)", paddingTop:14 }}>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", margin:"0 0 8px" }}>
                  Deposit Adjustments / Forfeit / Refund History
                </p>
                {((depositTxns.data as unknown as { transactions: { txn_id:string; txn_type:string; amount:number; notes?:string; created_at:string }[] }).transactions ?? []).map(tx => (
                  <div key={tx.txn_id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"8px 0", borderBottom:"1px solid var(--border-subtle)" }}>
                    <div>
                      <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{tx.txn_type.replace(/_/g," ")}</p>
                      {tx.notes && <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{tx.notes}</p>}
                    </div>
                    <div style={{ textAlign:"right" }}>
                      <p style={{ fontSize:12, fontWeight:700, color: tx.amount >= 0 ? "var(--success-text)" : "var(--danger-text)", margin:0 }}>
                        {tx.amount >= 0 ? "+" : ""}₹{Math.abs(tx.amount).toLocaleString("en-IN")}
                      </p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                        {new Date(tx.created_at).toLocaleDateString("en-IN")}
                      </p>
                    </div>
                  </div>
                ))}
                {((depositTxns.data as unknown as { transactions: unknown[] }).transactions ?? []).length === 0 && (
                  <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No deposit adjustments recorded.</p>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ COMPLAINTS & DISPUTES ════════════════════ */}
      {tab === "disputes" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
              <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Dispute Settlements</h3>
            </div>
            {settlements.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>{[...Array(3)].map((_,i) => <Skeleton key={i} height={36}/>)}</div>
            ) : (settlements.data?.settlements ?? []).length === 0 ? (
              <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>No disputes for this provider.</p>
            ) : (settlements.data?.settlements ?? []).map((s: DisputeSettlement, i, arr) => (
              <div key={s.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 20px",
                borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:12, fontWeight:500, color:"var(--text-primary)", margin:0 }}>{s.settlement_type?.replace(/_/g," ") ?? "Settlement"}</p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{s.admin_decision_reason ?? "—"}</p>
                </div>
                <Badge variant={s.settlement_status === "executed" ? "success" : s.settlement_status === "cancelled" ? "muted" : "warning"} size="sm">{s.settlement_status}</Badge>
                <span style={{ fontSize:12, fontWeight:600, minWidth:70, textAlign:"right" }}>{fmt(s.settlement_amount)}</span>
              </div>
            ))}
          </Card>
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
              <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Tenant Penalties</h3>
            </div>
            {penalties.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>{[...Array(3)].map((_,i) => <Skeleton key={i} height={36}/>)}</div>
            ) : (penalties.data?.penalties ?? []).length === 0 ? (
              <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>No penalties recorded.</p>
            ) : (penalties.data?.penalties ?? []).map((p, i, arr) => (
              <div key={p.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 20px",
                borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:12, fontWeight:500, color:"var(--text-primary)", margin:0 }}>{p.reason ?? "Penalty"}</p>
                </div>
                <Badge variant={p.status === "active" ? "danger" : "muted"} size="sm">{p.status}</Badge>
                <span style={{ fontSize:12, fontWeight:600, minWidth:70, textAlign:"right" }}>{fmt(p.amount)}</span>
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* ════════════════════ CUSTOMER SERVICE CREDIT SETTLEMENTS ════════════════════ */}
      {tab === "settlements" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"10px 14px", background:"var(--info-bg)", border:"1px solid var(--info-border)", borderRadius:8 }}>
            <p style={{ fontSize:12, color:"var(--info-text)", margin:0 }}>
              Customer service credit is platform credit issued to a customer, not a cash refund. Deduction is sourced from this
              provider&apos;s usage credits first, then security deposit only if policy allows and an admin approves.
            </p>
          </div>
          <Card padding={0}>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Settlement", "Status", "Credit Issued", "Usage Credit Deducted", "Deposit Deducted", "Created"].map(h => (
                    <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontSize:11, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(settlements.data?.settlements ?? []).filter((s: DisputeSettlement) => s.settlement_status === "executed").map((s: DisputeSettlement) => (
                  <tr key={s.id} style={{ borderBottom:"1px solid var(--border)" }}>
                    <td style={{ padding:"10px 14px", fontSize:12 }}>{s.id.slice(0, 8)}…</td>
                    <td style={{ padding:"10px 14px" }}><Badge variant="success" size="sm">{s.settlement_status}</Badge></td>
                    <td style={{ padding:"10px 14px", fontSize:12, fontWeight:600 }}>{fmt(s.settlement_amount)}</td>
                    <td style={{ padding:"10px 14px", fontSize:12 }}>{fmt(s.tenant_wallet_deduction_amount ?? 0)}</td>
                    <td style={{ padding:"10px 14px", fontSize:12 }}>{fmt(s.security_deposit_deduction_amount ?? 0)}</td>
                    <td style={{ padding:"10px 14px", fontSize:11, color:"var(--text-tertiary)" }}>{s.created_at ? new Date(s.created_at).toLocaleDateString("en-IN") : "—"}</td>
                  </tr>
                ))}
                {(settlements.data?.settlements ?? []).filter((s: DisputeSettlement) => s.settlement_status === "executed").length === 0 && (
                  <tr><td colSpan={6} style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13 }}>No executed settlements yet.</td></tr>
                )}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* ════════════════════ RISK & HEALTH ════════════════════ */}
      {tab === "risk-health" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14 }}>
            <StatCard label="Health Score" value={Math.round(t?.health_score ?? 0)} icon={<Zap/>} trend="neutral"/>
            <StatCard label="Health Band" value={t?.health_band?.replace(/_/g," ") ?? "—"} icon={<CheckCircle2/>} trend="neutral"/>
            <StatCard label="Open Complaints / Disputes" value={(settlements.data?.settlements ?? []).filter((s: DisputeSettlement) => s.settlement_status !== "executed" && s.settlement_status !== "cancelled").length} icon={<AlertCircle/>} trend="neutral"/>
          </div>
          <Card padding={20}>
            <p style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)", margin:"0 0 12px" }}>Health Factors</p>
            {health.loading ? <Skeleton height={100}/> : Object.keys(health.data?.signals ?? {}).length === 0 ? (
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No health signal data available yet.</p>
            ) : Object.entries(health.data?.signals ?? {}).map(([sig, rawScore]) => {
              const score = Number(rawScore) || 0;
              return (
                <div key={sig} style={{ marginBottom:10 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}>
                    <span style={{ fontSize:12, color:"var(--text-secondary)", textTransform:"capitalize" }}>{sig.replace(/_/g," ")}</span>
                    <span style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>{score.toFixed(0)}</span>
                  </div>
                  <div style={{ height:6, background:"var(--surface-sunken)", borderRadius:3, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${Math.min(100, Math.max(0, score))}%`,
                      background: score >= 70 ? "var(--success)" : score >= 40 ? "var(--warning)" : "var(--danger)" }}/>
                  </div>
                </div>
              );
            })}
          </Card>
        </div>
      )}

      {/* ════════════════════ USAGE CREDIT LEDGER ════════════════════ */}
      {tab === "wallet" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"10px 14px", background:"var(--info-bg)", border:"1px solid var(--info-border)", borderRadius:8 }}>
            <p style={{ fontSize:12, color:"var(--info-text)", margin:0 }}>
              Usage credits are internal ServiceOS credits used for platform charges. They are not cash, not withdrawable, and not a payout balance.
              Customers pay this provider directly — ServiceOS does not collect service payment for Home Services.
            </p>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14 }}>
            {wallet.loading ? [...Array(3)].map((_,i) => <Skeleton key={i} height={100} style={{ borderRadius:14 }}/>) : <>
              <StatCard label="Usage Credit Balance" value={fmt(w?.credit_balance ?? w?.balance ?? 0)} icon={<CreditCard/>}
                trend={w?.low_balance_alert ? "down" : "neutral"} alert={!!w?.low_balance_alert}/>
              <StatCard label="Lifetime Top-ups" value={fmt(w?.lifetime_purchased ?? 0)} icon={<Clock/>} trend="neutral"/>
              <StatCard label="Completed Job Credit Deductions"  value={fmt(w?.lifetime_consumed  ?? 0)} icon={<CheckCircle2/>}
                trend="neutral" alert={false}/>
            </>}
          </div>
          <div style={{ display:"flex", justifyContent:"flex-end" }}>
            <Btn icon={<CreditCard size={14}/>} onClick={() => setCreditOpen(true)}>Add Usage Credits</Btn>
          </div>
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
              <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Usage Credit Ledger</h3>
            </div>
            {txns.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(6)].map((_,i) => <Skeleton key={i} height={34}/>)}
              </div>
            ) : (txns.data?.entries ?? []).length === 0 ? (
              <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                No ledger entries yet
              </p>
            ) : (txns.data?.entries ?? []).map((e, i, arr) => (
              <div key={e.ledger_id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 20px",
                borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div style={{ width:28, height:28, borderRadius:"50%", flexShrink:0,
                  background: e.credit_delta >= 0 ? "var(--success-bg)" : "var(--danger-bg)",
                  display:"flex", alignItems:"center", justifyContent:"center", fontSize:14 }}>
                  {e.credit_delta >= 0 ? "↓" : "↑"}
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:12, fontWeight:500, color:"var(--text-primary)", margin:0 }}>
                    {(e.event_type ?? "").replace(/_/g," ")}
                    {e.job_id && ` · Job ${e.job_id.slice(0,8)}`}
                  </p>
                  {e.reason && (
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{e.reason}</p>
                  )}
                </div>
                <div style={{ textAlign:"right" }}>
                  <p style={{ fontSize:13, fontWeight:700, margin:0,
                    color: e.credit_delta >= 0 ? "var(--success-text)" : "var(--danger-text)" }}>
                    {e.credit_delta >= 0 ? "+" : ""}{fmt(e.credit_delta)}
                  </p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                    bal: {fmt(e.balance_after)} · {new Date(e.created_at).toLocaleDateString("en-IN")}
                  </p>
                </div>
              </div>
            ))}
          </Card>
        </div>
      )}

      {/* ════════════════════ MEDIA / PHOTOS ════════════════════ */}
      {tab === "media" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {mediaQuota.data && (
            <Card padding={16}>
              <p style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)", margin:"0 0 8px" }}>Storage Quota</p>
              <div style={{ display:"flex", gap:24 }}>
                {[
                  ["Used",       `${((mediaQuota.data.used_bytes ?? 0) / 1_048_576).toFixed(1)} MB`],
                  ["Limit",      `${((mediaQuota.data.limit_bytes ?? 0) / 1_073_741_824).toFixed(1)} GB`],
                  ["Files",      String(mediaQuota.data.file_count)],
                  ["File Limit", String(mediaQuota.data.file_limit)],
                ].map(([label, val]) => (
                  <div key={label}>
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 2px", textTransform:"uppercase" }}>{label}</p>
                    <p style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{val}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)" }}>
              <p style={{ fontSize:13, fontWeight:700, margin:0, color:"var(--text-primary)" }}>
                Files ({(media.data as unknown as { files?: unknown[] })?.files?.length ?? 0})
              </p>
            </div>
            {media.loading ? (
              <div style={{ padding:16, display:"flex", flexWrap:"wrap", gap:12 }}>
                {[...Array(6)].map((_,i) => <Skeleton key={i} height={90} style={{ width:140, borderRadius:8 }}/>)}
              </div>
            ) : ((media.data as unknown as { files?: MediaFile[] })?.files ?? []).length === 0 ? (
              <div style={{ padding:"40px 20px", textAlign:"center" }}>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No files uploaded.</p>
              </div>
            ) : (
              <div style={{ padding:16, display:"flex", flexWrap:"wrap", gap:12 }}>
                {((media.data as unknown as { files: MediaFile[] }).files ?? []).map((f: MediaFile) => (
                  <div key={f.file_id} style={{ width:140, border:"1px solid var(--border)", borderRadius:8,
                    overflow:"hidden", background:"var(--surface-sunken)" }}>
                    {f.content_type?.startsWith("image/") && f.url ? (
                      <img src={f.url} alt={f.filename} style={{ width:"100%", height:80, objectFit:"cover", display:"block" }}/>
                    ) : (
                      <div style={{ width:"100%", height:80, display:"flex", alignItems:"center",
                        justifyContent:"center", background:"var(--bg)" }}>
                        <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{f.content_type?.split("/")[1] ?? "file"}</span>
                      </div>
                    )}
                    <div style={{ padding:"6px 8px" }}>
                      <p style={{ fontSize:11, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px",
                        overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f.filename}</p>
                      <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"0 0 6px" }}>
                        {f.purpose?.replace(/_/g," ")} · {((f.size_bytes ?? 0) / 1024).toFixed(0)} KB
                      </p>
                      <button onClick={async () => { const res = await deleteMediaAction.execute(f.file_id); if (res !== null) media.refetch(); }}
                        style={{ fontSize:10, color:"var(--danger-text)", background:"none", border:"none",
                          cursor:"pointer", padding:0, fontFamily:"inherit" }}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ JOBS ════════════════════ */}
      {tab === "jobs" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
            display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Jobs</h3>
            <Btn size="xs" variant="ghost" onClick={() => allJobs.refetch()}>↻ Refresh</Btn>
          </div>
          {allJobs.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : (allJobs.data?.items ?? []).length === 0 ? (
            <div style={{ padding:"48px 20px", textAlign:"center" }}>
              <div style={{ marginBottom:12 }}><Briefcase size={32} style={{ color:"var(--text-tertiary)" }}/></div>
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No jobs yet</p>
            </div>
          ) : (
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Job #","City","Staff","Status","Collected Amount","Completed Job Deduction","Date"].map(h => (
                    <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(allJobs.data?.items ?? []).map((j, i, arr) => (
                  <tr key={j.id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding:"11px 16px", fontWeight:600, fontSize:12, fontFamily:"monospace", color:"var(--text-primary)" }}>
                      <a href={`/admin/home-services/service-jobs/${j.id}`} style={{ color:"inherit", textDecoration:"none" }}>
                        {j.job_number}
                      </a>
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                      {j.city ?? "—"}{j.zipcode ? ` / ${j.zipcode}` : ""}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>{j.assigned_staff_id ? "Assigned" : "Unassigned"}</td>
                    <td style={{ padding:"11px 16px" }}><JobStatusBadge status={j.status}/></td>
                    <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--success-text)" }}>
                      {j.collected_amount != null ? fmt(j.collected_amount) : "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>
                      {j.completed_job_deduction_credits != null ? `${j.completed_job_deduction_credits} credits` : "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:11, color:"var(--text-tertiary)" }}>
                      {j.created_at ? new Date(j.created_at).toLocaleDateString("en-IN") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* ════════════════════ BOOKINGS ════════════════════ */}
      {tab === "bookings" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
            display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Bookings</h3>
            <Btn size="xs" variant="ghost" onClick={() => allBookings.refetch()}>↻ Refresh</Btn>
          </div>
          {allBookings.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height={48}/>)}
            </div>
          ) : (allBookings.data?.bookings ?? []).length === 0 ? (
            <div style={{ padding:"48px 20px", textAlign:"center" }}>
              <div style={{ marginBottom:12 }}><CalendarCheck size={32} style={{ color:"var(--text-tertiary)" }}/></div>
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No bookings yet</p>
            </div>
          ) : (
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Booking #","Service","Status","Preferred Date","Service Price","ServiceOS Credit Applied","Payable To Provider","Created"].map(h => (
                    <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(allBookings.data?.bookings ?? []).map((bk: Booking, i, arr) => (
                  <tr key={bk.booking_id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding:"11px 16px", fontWeight:600, fontSize:12, fontFamily:"monospace", color:"var(--text-primary)" }}>
                      {bk.booking_number}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>{bk.service_type_id}</td>
                    <td style={{ padding:"11px 16px" }}>
                      <Badge variant={BOOKING_VARIANT[bk.status] ?? "muted"} size="sm">{bk.status.replace(/_/g," ")}</Badge>
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                      {bk.preferred_date ?? "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--text-primary)" }}>
                      {bk.quoted_price != null ? fmt(bk.quoted_price) : "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                      {bk.credit_applied != null && bk.credit_applied > 0 ? fmt(bk.credit_applied) : "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:12, fontWeight:600, color:"var(--success-text)" }}>
                      {(bk.payable_amount ?? bk.quoted_price) != null ? fmt((bk.payable_amount ?? bk.quoted_price)!) : "—"}
                    </td>
                    <td style={{ padding:"11px 16px", fontSize:11, color:"var(--text-tertiary)" }}>
                      {new Date(bk.created_at).toLocaleDateString("en-IN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* ════════════════════ REVIEWS ════════════════════ */}
      {tab === "reviews" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {/* Aggregate */}
          {revAgg.data && (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
              <StatCard label="Avg Rating"    value={revAgg.data.avg_composite?.toFixed(1) ?? "—"} icon={<Star/>} trend="neutral"/>
              <StatCard label="Total Reviews" value={revAgg.data.review_count ?? 0}               icon={<Users/>} trend="neutral"/>
              <StatCard label="Reply Rate"    value={`${revAgg.data.reply_rate ?? 0}%`}            icon={<CheckCircle2/>} trend="neutral"/>
              <StatCard label="Reply Rate"    value={`${revAgg.data.reply_rate ?? 0}%`}            icon={<Clock/>} trend="neutral"/>
            </div>
          )}
          <Card padding={0}>
            <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
              display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>All Reviews</h3>
              <Btn size="xs" variant="ghost" onClick={() => allReviews.refetch()}>↻ Refresh</Btn>
            </div>
            {allReviews.loading ? (
              <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(5)].map((_,i) => <Skeleton key={i} height={80}/>)}
              </div>
            ) : ((allReviews.data as unknown as { reviews?: unknown[] })?.reviews ?? []).length === 0 ? (
              <div style={{ padding:"48px 20px", textAlign:"center" }}>
                <div style={{ marginBottom:12 }}><Star size={32} style={{ color:"var(--text-tertiary)" }}/></div>
                <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>No reviews yet</p>
              </div>
            ) : (
              ((allReviews.data as unknown as { reviews: Record<string, unknown>[] })?.reviews ?? []).map((rv, i, arr) => (
                <div key={String(rv.review_id ?? rv.id ?? i)} style={{ padding:"14px 20px",
                  borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:6 }}>
                    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                      <span style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)" }}>
                        {"⭐".repeat(Math.round(Number(rv.rating ?? rv.overall_rating ?? 0)))}
                      </span>
                      <Badge variant="muted" size="sm">{String(rv.status ?? "")}</Badge>
                    </div>
                    <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
                      {rv.created_at ? new Date(String(rv.created_at)).toLocaleDateString("en-IN") : "—"}
                    </span>
                  </div>
                  {rv.review_text && (
                    <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>{String(rv.review_text)}</p>
                  )}
                  {rv.tenant_reply && (
                    <div style={{ marginTop:8, padding:"8px 12px", background:"var(--surface-sunken)", borderRadius:8,
                      borderLeft:"3px solid var(--brand)" }}>
                      <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                        <strong>Reply:</strong> {String(rv.tenant_reply)}
                      </p>
                    </div>
                  )}
                </div>
              ))
            )}
          </Card>
        </div>
      )}

      {/* ════════════════════ AUDIT LOGS ════════════════════ */}
      {tab === "audit" && (
        <Card padding={0}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid var(--border)",
            display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <h3 style={{ fontSize:14, fontWeight:600, margin:0 }}>Audit Log</h3>
            <Btn size="xs" variant="ghost" onClick={() => audit.refetch()}>↻ Refresh</Btn>
          </div>
          {audit.loading ? (
            <div style={{ padding:16, display:"flex", flexDirection:"column", gap:8 }}>
              {[...Array(8)].map((_,i) => <Skeleton key={i} height={42}/>)}
            </div>
          ) : (audit.data?.logs ?? []).length === 0 ? (
            <p style={{ padding:"32px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
              No audit entries
            </p>
          ) : (audit.data?.logs ?? []).map((log: TenantAuditLog, i, arr) => (
            <div key={log.log_id} style={{ display:"flex", alignItems:"flex-start", gap:12, padding:"12px 20px",
              borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div style={{ width:28, height:28, borderRadius:"50%", background:"var(--surface-sunken)", flexShrink:0,
                display:"flex", alignItems:"center", justifyContent:"center", fontSize:12 }}>📋</div>
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0,
                  fontFamily:"monospace" }}>{log.operation}</p>
                {log.actor_id && (
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>by {log.actor_id}</p>
                )}
              </div>
              <span style={{ fontSize:11, color:"var(--text-tertiary)", whiteSpace:"nowrap" }}>
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </Card>
      )}

      {/* ════════════════════ ONBOARDING ════════════════════ */}
      {tab === "onboarding" && <OnboardingAdminTab tenantId={id}/>}

      {/* ════════════════════ PROVIDER OFFERINGS ════════════════════ */}
      {tab === "provider-offerings" && <ProviderOfferingsTab tenantId={id}/>}

      {/* ════════════════════ PROVIDER COVERAGE AREAS ════════════════════ */}
      {tab === "provider-areas" && <ProviderAreasTab tenantId={id} refreshToken={areasRefreshToken}/>}

      {/* ════════════════════ PROVIDER TEAM ════════════════════ */}
      {tab === "provider-team" && <ProviderTeamTab tenantId={id}/>}

      {/* ════════════════════ PROVIDER AVAILABILITY ════════════════════ */}
      {tab === "provider-availability" && <ProviderAvailabilityTab tenantId={id}/>}

      {/* ════════════════════ BOOKABILITY ════════════════════ */}
      {tab === "bookability" && <BookabilityTab tenantId={id}/>}

      {/* ── Adjust Deposit Modal ──────────────────────────────────────────────── */}
      <Modal open={adjDepositOpen} onClose={() => setAdjDepositOpen(false)} title="Adjust Security Deposit" size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Positive amount credits the deposit; negative debits it.
          </p>
          {adjustDepositAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{adjustDepositAction.error}</p>
          )}
          <Input label="Amount (₹)" placeholder="5000 or -1000" value={adjAmt} onChange={setAdjAmt} type="number"/>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)", textTransform:"uppercase",
              display:"block", marginBottom:4 }}>Category</label>
            <select value={adjCategory} onChange={e => setAdjCategory(e.target.value as typeof adjCategory)}
              style={{ width:"100%", padding:"8px 10px", borderRadius:8, border:"1px solid var(--border)",
                background:"var(--bg)", color:"var(--text-primary)", fontSize:13, fontFamily:"inherit" }}>
              <option value="correction">Correction</option>
              <option value="goodwill">Goodwill</option>
              <option value="dispute">Dispute</option>
              <option value="refund">Refund</option>
            </select>
          </div>
          <Input label="Reason (min 10 chars)" placeholder="Explain the reason for adjustment…" value={adjReason} onChange={setAdjReason}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setAdjDepositOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={adjustDepositAction.loading}
              disabled={!adjAmt || adjReason.length < 10}
              onClick={async () => {
                const res = await adjustDepositAction.execute(Number(adjAmt), adjReason, adjCategory);
                if (res !== null) {
                  deposit.refetch(); depositTxns.refetch();
                  setAdjDepositOpen(false); setAdjAmt(""); setAdjReason(""); setAdjCategory("correction");
                  notify("Deposit adjusted.");
                }
              }}>Apply Adjustment</Btn>
          </div>
        </div>
      </Modal>

      {/* ── Add Credits Modal ──────────────────────────────────────────────────── */}
      <Modal open={creditOpen} onClose={() => setCreditOpen(false)} title="Add Usage Credits" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"12px 16px", borderRadius:10, background:"rgba(37,99,235,0.06)", border:"1px solid rgba(37,99,235,0.2)" }}>
            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
              Add usage credits to <strong>{t?.tenant_name}</strong>. Usage credits are internal platform credits —
              not cash, not withdrawable. This will increase the provider's credit balance and may allow completed job deductions.
            </p>
            {w && <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:"6px 0 0" }}>
              Current balance: {fmt(w.credit_balance ?? w.balance ?? 0)}
            </p>}
          </div>
          {creditAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{creditAction.error}</p>
            </div>
          )}
          <Input label="Amount (credits)" placeholder="e.g. 1000" value={creditAmt} onChange={setCreditAmt} type="number"/>
          <Input label="Reason *" placeholder="Onboarding bonus, top-up, correction…" value={creditNote} onChange={setCreditNote}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setCreditOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={creditAction.loading} disabled={!creditAmt || !creditNote.trim()} onClick={handleCredit}>
              Add {creditAmt || "0"} Credits
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Suspend Modal ─────────────────────────────────────────────────────── */}
      <Modal open={suspendOpen} onClose={() => setSuspendOpen(false)} title="Suspend Tenant" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>
              This will immediately halt all operations for <strong>{t?.tenant_name}</strong>.
            </p>
          </div>
          {suspendAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{suspendAction.error}</p>
            </div>
          )}
          <Input label="Reason" placeholder="Policy violation, unpaid balance…" value={suspendMsg} onChange={setSuspendMsg}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setSuspendOpen(false)}>Cancel</Btn>
            <Btn variant="danger" size="sm" loading={suspendAction.loading} onClick={handleSuspend}>
              Confirm Suspension
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Change Plan Modal ─────────────────────────────────────────────────── */}
      <Modal open={planModal} onClose={() => setPlanModal(false)} title="Change Plan" size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Current plan: <strong>{t?.plan_type ?? "—"}</strong>
          </p>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              New Plan
            </label>
            <select value={newPlan} onChange={e => setNewPlan(e.target.value)}
              style={{ width:"100%", height:38, padding:"0 12px", border:"1px solid var(--border)", borderRadius:10,
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13, outline:"none" }}>
              <option value="starter">Starter</option>
              <option value="growth">Growth</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Reason <span style={{ color:"var(--danger)" }}>*</span>
            </label>
            <textarea value={planReason} onChange={e => setPlanReason(e.target.value)} rows={2}
              placeholder="Why is this plan change being made?"
              style={{ width:"100%", padding:"8px 10px", borderRadius:8, border:"1px solid var(--border)",
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13, fontFamily:"inherit", boxSizing:"border-box" }} />
          </div>
          {upgradePlanAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{upgradePlanAction.error}</p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setPlanModal(false)}>Cancel</Btn>
            <Btn size="sm" loading={upgradePlanAction.loading} disabled={!planReason.trim()} onClick={handleUpgradePlan}>
              Apply Plan Change
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Reinstate Modal ───────────────────────────────────────────────────── */}
      <Modal open={reinstateOpen} onClose={() => setReinstateOpen(false)} title="Reinstate Tenant" size="sm">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            This will restore active status and re-enable discoverability for <strong>{t?.tenant_name}</strong>.
          </p>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Reason <span style={{ color:"var(--danger)" }}>*</span>
            </label>
            <textarea value={reinstateMsg} onChange={e => setReinstateMsg(e.target.value)} rows={2}
              placeholder="Why is this tenant being reinstated?"
              style={{ width:"100%", padding:"8px 10px", borderRadius:8, border:"1px solid var(--border)",
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13, fontFamily:"inherit", boxSizing:"border-box" }} />
          </div>
          {reinstateAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{reinstateAction.error}</p>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setReinstateOpen(false)}>Cancel</Btn>
            <Btn variant="success" size="sm" loading={reinstateAction.loading} disabled={!reinstateMsg.trim()} onClick={handleReinstate}>
              Reinstate Tenant
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Request Changes Modal ─────────────────────────────────────────────── */}
      <Modal open={reqChangesOpen} onClose={() => setReqChangesOpen(false)} title="Request Changes" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Notify <strong>{t?.tenant_name}</strong> that changes are required before their profile can proceed.
          </p>
          {requestChangesAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{requestChangesAction.error}</p>
          )}
          <Input label="Reason *" placeholder="What needs to change?" value={reqChangesMsg} onChange={setReqChangesMsg}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setReqChangesOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={requestChangesAction.loading} disabled={!reqChangesMsg.trim()} onClick={handleRequestChanges}>
              Send Request
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Send Notification Modal ───────────────────────────────────────────── */}
      <Modal open={notifyOpen} onClose={() => setNotifyOpen(false)} title="Send Notification" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          {sendNotificationAction.error && (
            <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{sendNotificationAction.error}</p>
          )}
          <Input label="Subject" placeholder="Subject" value={notifySubject} onChange={setNotifySubject}/>
          <Input label="Message *" placeholder="Message to tenant…" value={notifyMsg} onChange={setNotifyMsg}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setNotifyOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={sendNotificationAction.loading} disabled={!notifyMsg.trim()} onClick={handleSendNotification}>
              Send
            </Btn>
          </div>
        </div>
      </Modal>

      {/* ── Add Staff Modal (Sprint 4) ────────────────────────────────────────── */}
      <Modal open={addStaffOpen} onClose={() => setAddStaffOpen(false)} title="Add Staff Member" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {addStaffAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{addStaffAction.error}</p>
            </div>
          )}
          <Input label="Full Name" placeholder="Ravi Kumar" value={staffName} onChange={setStaffName}/>
          <Input label="Email" placeholder="ravi@example.com" value={staffEmail} onChange={setStaffEmail}/>
          <Input label="Phone" placeholder="+91 9876543210" value={staffPhone} onChange={setStaffPhone}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:4 }}>
            <Btn variant="ghost" size="sm" onClick={() => setAddStaffOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={addStaffAction.loading} onClick={async () => {
              const res = await addStaffAction.execute({ name:staffName, email:staffEmail, phone:staffPhone });
              if (res !== null) {
                staff.refetch();
                setAddStaffOpen(false);
                setStaffName(""); setStaffEmail(""); setStaffPhone("");
                notify(`Staff "${staffName}" added. Temp password: ${(res as { temp_password?: string }).temp_password ?? "—"}`);
              }
            }}>Add Staff</Btn>
          </div>
        </div>
      </Modal>

      {/* ── Add User Modal (Sprint 4) ─────────────────────────────────────────── */}
      <Modal open={addUserOpen} onClose={() => setAddUserOpen(false)} title="Add Tenant User" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {addUserAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{addUserAction.error}</p>
            </div>
          )}
          <Input label="Full Name" placeholder="Priya Sharma" value={userName} onChange={setUserName}/>
          <Input label="Email" placeholder="priya@company.com" value={userEmail} onChange={setUserEmail}/>
          <Input label="Phone" placeholder="+91 9876543210" value={userPhone} onChange={setUserPhone}/>
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>Role</label>
            <select value={userRole} onChange={e => setUserRole(e.target.value)}
              style={{ width:"100%", height:38, padding:"0 12px", border:"1px solid var(--border)", borderRadius:10,
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13, outline:"none" }}>
              <option value="tenant_owner">Owner</option>
              <option value="tenant_manager">Manager</option>
              <option value="tenant_finance">Finance</option>
              <option value="tenant_support">Support</option>
            </select>
          </div>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:4 }}>
            <Btn variant="ghost" size="sm" onClick={() => setAddUserOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={addUserAction.loading} onClick={async () => {
              const res = await addUserAction.execute({ name:userName, email:userEmail, phone:userPhone, role:userRole });
              if (res !== null) {
                users.refetch();
                setAddUserOpen(false);
                setUserName(""); setUserEmail(""); setUserPhone(""); setUserRole("tenant_manager");
                notify(`User "${userName}" added. Temp password: ${(res as { temp_password?: string }).temp_password ?? "—"}`);
              }
            }}>Add User</Btn>
          </div>
        </div>
      </Modal>

      {/* ── Add Service Area Modal (Sprint 4) ────────────────────────────────── */}
      <Modal open={addAreaOpen} onClose={() => setAddAreaOpen(false)} title="Add Service Area" size="md">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {addAreaAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{addAreaAction.error}</p>
            </div>
          )}
          <div>
            <label style={{ fontSize:12, fontWeight:600, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>Coverage Type</label>
            <select value={areaCoverage} onChange={e => setAreaCoverage(e.target.value)}
              style={{ width:"100%", height:38, padding:"0 12px", border:"1px solid var(--border)", borderRadius:10,
                background:"var(--surface)", color:"var(--text-primary)", fontSize:13, outline:"none" }}>
              <option value="city">City</option>
              <option value="zipcode">Zipcode</option>
              <option value="zone">Zone</option>
              <option value="radius">Radius</option>
            </select>
          </div>
          <Input label="City" placeholder="Ludhiana" value={areaCity} onChange={setAreaCity}/>
          <Input label="State" placeholder="Punjab" value={areaState} onChange={setAreaState}/>
          <Input label="Zipcode (optional)" placeholder="141001" value={areaZipcode} onChange={setAreaZipcode}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:4 }}>
            <Btn variant="ghost" size="sm" onClick={() => setAddAreaOpen(false)}>Cancel</Btn>
            <Btn size="sm" loading={addAreaAction.loading} onClick={async () => {
              const res = await addAreaAction.execute({
                city:areaCity, state:areaState,
                zipcode:areaZipcode || undefined,
                coverage_type:areaCoverage,
              });
              if (res !== null) {
                setAreasRefreshToken(t => t + 1);
                setAddAreaOpen(false);
                setAreaCity(""); setAreaState(""); setAreaZipcode(""); setAreaCoverage("city");
                notify(`Service area for ${areaCity} added.`);
              }
            }}>Add Area</Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}

export default function Tenant360Page({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<div style={{ padding: 40 }}>Loading…</div>}>
      <Tenant360PageInner params={params} />
    </Suspense>
  );
}
