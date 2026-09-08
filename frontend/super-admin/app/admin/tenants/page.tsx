"use client";
import React, { useState, useCallback, Suspense } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  StatCard, Badge, Btn, Modal, DataTable,
} from "../../../components/shared/ui";
import { ActionMenu } from "../../../components/shared/layout";
import { resolveMediaUrl } from "../../../components/shared/ProfilePhotoUploader";
import EnterpriseFilterBar from "../../../components/enterprise/EnterpriseFilterBar";
import { Card, PageHeader, Pagination, StatusBadge } from "@serviceos/design-system";
import {
  Search, RefreshCw, Users, CheckCircle, Clock, AlertCircle, XCircle,
  Download, Eye, Archive, Flag, Shield, X, Filter, ChevronDown, ChevronLeft,
  ChevronRight, Building2, UserCheck, MapPin, Zap, TrendingUp,
  TrendingDown, Bell, CreditCard, RotateCcw, Plus,
  BarChart2, Activity, Layers, Lock, Settings, ExternalLink, Edit,
} from "lucide-react";
import {
  adminTenantsApi,
  type TenantListItem, type TenantsSummary, type TenantsInsights,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmtDate = (iso: string | null | undefined) => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};
const timeAgo = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const secs = (Date.now() - new Date(iso).getTime()) / 1000;
  if (secs < 60) return "Just now";
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
};

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";

const STATUS_V: Record<string, BV> = {
  active: "success", pending_review: "warning", pending_setup: "info",
  changes_requested: "warning", suspended: "danger", rejected: "danger",
  onboarding_pending: "muted", archived: "muted", deactivated: "muted",
  inactive: "muted",
};
const VERIF_V: Record<string, BV> = {
  not_started: "muted", pending: "warning", under_review: "warning",
  in_progress: "info", approved: "success", verified: "success",
  completed: "success", changes_requested: "warning", rejected: "danger", expired: "danger",
};
const STATUS_LABEL: Record<string, string> = {
  active: "Active", pending_review: "Pending Review", pending_setup: "Pending Setup",
  changes_requested: "Changes Requested", suspended: "Suspended", rejected: "Rejected",
  onboarding_pending: "Onboarding", archived: "Archived", deactivated: "Deactivated",
  inactive: "Inactive",
};
const VERIF_LABEL: Record<string, string> = {
  not_started: "Not Started", pending: "Pending", under_review: "Under Review",
  in_progress: "In Progress", approved: "Approved", verified: "Verified",
  completed: "Completed", changes_requested: "Changes Requested",
  rejected: "Rejected", expired: "Expired",
};
const VERTICAL_LABEL: Record<string, string> = {
  home_services: "Home Services", beauty: "Beauty & Wellness", salon: "Salon",
  coaching: "Coaching / IELTS", real_estate: "Real Estate", automotive: "Automotive",
  pest_control: "Pest Control", cleaning: "Cleaning", cleaning_services: "Cleaning",
  laundry: "Laundry", restaurant: "Restaurant", pharmacy: "Pharmacy",
  repair_services: "Repair Services", professional_services: "Prof. Services",
};
const humanize = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

const PAGE_SIZE = 25;

// ── Interfaces ─────────────────────────────────────────────────────────────────

interface Filters {
  q: string; status: string; verification_status: string;
  city_tier: string; state: string; city: string; created_from: string; created_to: string;
  sort_by: string; sort_dir: string;
}
const DEFAULT_FILTERS: Filters = {
  q: "", status: "", verification_status: "",
  city_tier: "", state: "", city: "", created_from: "", created_to: "",
  sort_by: "created_at", sort_dir: "desc",
};

type ActiveModal =
  | { type: "add_credits"; tenant: TenantListItem }
  | { type: "suspend"; tenant: TenantListItem }
  | { type: "request_changes"; tenant: TenantListItem }
  | { type: "send_notification"; tenant: TenantListItem }
  | null;

type Row = TenantListItem & Record<string, unknown>;

// ── KPI Cards ─────────────────────────────────────────────────────────────────

function KpiCards({ s, loading, onFilter }: {
  s: TenantsSummary | null; loading: boolean;
  onFilter: (f: Partial<Filters>) => void;
}) {
  const v = s ?? { total: 0, active: 0, pending_review: 0, pending_setup: 0, changes_requested: 0, suspended: 0, rejected: 0 };

  const cards: { label: string; value: number; accent: string; icon: React.ReactNode; filter: Partial<Filters>; alert?: boolean }[] = [
    { label: "Total Providers",       value: v.total,                     accent: "var(--brand)", icon: <Building2 />, filter: {} },
    { label: "Active",                value: v.active,                    accent: "var(--success)",     icon: <CheckCircle />, filter: { status: "active" } },
    { label: "Pending Review",        value: v.pending_review,            accent: "var(--warning)",     icon: <Clock />, filter: { verification_status: "pending" } },
    { label: "Pending Setup",         value: v.pending_setup,             accent: "#6366f1",     icon: <Settings />, filter: { verification_status: "not_started" } },
    { label: "Changes Requested",     value: v.changes_requested,         accent: "#2f9e8f",     icon: <Edit />, filter: { verification_status: "changes_requested" } },
    { label: "Suspended",             value: v.suspended,                 accent: "var(--danger)",     icon: <Lock />, filter: { status: "suspended" }, alert: v.suspended > 0 },
    { label: "Rejected",              value: v.rejected,                  accent: "#9ca3af",     icon: <XCircle />, filter: { status: "rejected" } },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10, marginBottom: 20 }}>
      {cards.map(c => (
        <StatCard
          key={c.label}
          label={c.label}
          value={loading ? "…" : c.value.toLocaleString()}
          icon={c.icon}
          accent={c.accent}
          alert={c.alert}
          onClick={() => onFilter(c.filter)}
        />
      ))}
    </div>
  );
}

// ── Filter Toolbar ─────────────────────────────────────────────────────────────

function Toolbar({ filters, onChange, onExport, onRefresh, onAdd }: {
  filters: Filters; onChange: (f: Filters) => void;
  onExport: () => void; onRefresh: () => void; onAdd: () => void;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <EnterpriseFilterBar
        searchValue={filters.q}
        onSearch={q => onChange({ ...filters, q })}
        filters={[
          { key: "status", label: "Status", type: "select", options: Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label })) },
          { key: "verification_status", label: "Verification", type: "select", options: Object.entries(VERIF_LABEL).map(([value, label]) => ({ value, label })) },
          { key: "city_tier", label: "City tier", type: "select", advanced: true, group: "Location", options: [{ value: "metro", label: "Metro" }, { value: "large", label: "Large city" }, { value: "mid", label: "Mid-size" }, { value: "small", label: "Small town" }] },
          { key: "state", label: "State", type: "text", advanced: true, group: "Location" },
          { key: "city", label: "City", type: "text", advanced: true, group: "Location" },
          { key: "created", label: "Created", type: "date_range", advanced: true, group: "Lifecycle" },
          { key: "sort_by", label: "Sort by", type: "select", advanced: true, group: "Ordering", options: [{ value: "created_at", label: "Created" }, { value: "updated_at", label: "Updated" }, { value: "tenant_name", label: "Name" }, { value: "health_score", label: "Health" }] },
          { key: "sort_dir", label: "Direction", type: "select", advanced: true, group: "Ordering", options: [{ value: "desc", label: "Descending" }, { value: "asc", label: "Ascending" }] },
        ]}
        values={{ ...filters, created_from: filters.created_from, created_to: filters.created_to }}
        onChange={(key, value) => {
          const mapped = key === "created_from" ? "created_from" : key === "created_to" ? "created_to" : key;
          onChange({ ...filters, [mapped]: value });
        }}
        onBatchChange={changes => onChange({ ...filters, ...changes, created_from: changes.created_from ?? filters.created_from, created_to: changes.created_to ?? filters.created_to })}
        onReset={() => onChange(DEFAULT_FILTERS)}
        rightSlot={<div style={{ display: "flex", gap: 6 }}>
          <Btn variant="secondary" size="sm" onClick={onExport}><Download size={12} /> Export</Btn>
          <Btn variant="secondary" size="sm" onClick={onRefresh}><RefreshCw size={12} /></Btn>
          <Btn variant="primary" size="sm" onClick={onAdd}><Plus size={12} /> Add tenant</Btn>
        </div>}
      />
    </div>
  );
}

// ── Active Filter Chips ────────────────────────────────────────────────────────

// ── Bulk Action Bar ────────────────────────────────────────────────────────────

function BulkBar({ count, onSuspend, onClear }: { count: number; onSuspend: () => void; onClear: () => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", background: "var(--accent-muted, var(--accent-muted))", border: "1px solid var(--border)", borderRadius:"var(--radius-md)", marginBottom: 12 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent, var(--brand))" }}>{count} selected</span>
      <Btn variant="danger" size="sm" onClick={onSuspend}><Lock size={12} /> Suspend All</Btn>
      <button onClick={onClear} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}><X size={14} /></button>
    </div>
  );
}

// ── Row Action Menu ────────────────────────────────────────────────────────────

function TenantActions({ row, onAction }: {
  row: TenantListItem;
  onAction: (type: string, tenant: TenantListItem) => void;
}) {
  const items = [
    { label: "View Details",       icon: <Eye size={12} />,        action: "view" },
    { label: "Open 360",           icon: <ExternalLink size={12} />, action: "360" },
    { label: "Review Verification",icon: <UserCheck size={12} />,  action: "verify", divider: true },
    { label: "Request Changes",    icon: <Edit size={12} />,       action: "request_changes" },
    { label: "Add Usage Credits",  icon: <CreditCard size={12} />, action: "add_credits" },
    { label: "Send Notification",  icon: <Bell size={12} />,       action: "send_notification", divider: true },
    { label: "View Audit Logs",    icon: <Activity size={12} />,   action: "audit" },
    ...(row.status !== "suspended"
      ? [{ label: "Suspend Tenant", icon: <Lock size={12} />, action: "suspend", danger: true, divider: true }]
      : [{ label: "Reactivate",     icon: <RotateCcw size={12} />, action: "reactivate", divider: true }]
    ),
  ];

  return (
    <ActionMenu
      size="xs"
      items={items.map(item => ({
        label: item.label,
        icon: item.icon,
        divider: item.divider,
        variant: item.danger ? "danger" as const : "default" as const,
        onClick: () => onAction(item.action, row),
      }))}
    />
  );
}

// ── Verification Progress Cell ─────────────────────────────────────────────────

function VerifCell({ status }: { status: string }) {
  return (
    <div>
      <StatusBadge status={status} size="sm" />
    </div>
  );
}

// ── Tenant Name Cell ───────────────────────────────────────────────────────────

function TenantCell({ row }: { row: TenantListItem }) {
  const initials = (row.business_name || row.tenant_name || "?").slice(0, 2).toUpperCase();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius:"var(--radius-md)", background: "var(--brand)20", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13, color: "var(--brand)", flexShrink: 0 }}>
        {row.logo_url
          ? <img src={resolveMediaUrl(row.logo_url) ?? undefined} alt="" style={{ width: 36, height: 36, borderRadius:"var(--radius-md)", objectFit: "cover" }} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          : initials
        }
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {row.business_name || row.tenant_name}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {row.email || row.phone || "—"}
        </div>
        {row.owner_name && (
          <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{row.owner_name}</div>
        )}
      </div>
    </div>
  );
}

// ── Credits Cell ───────────────────────────────────────────────────────────────

function CreditsCell({ balance }: { balance: number }) {
  const low = balance < 500;
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, fontVariantNumeric: "tabular-nums", color: low ? "var(--danger)" : "var(--text)" }}>
        ₹{balance.toLocaleString("en-IN")}
      </div>
      {low && <Badge variant="danger" size="sm">Low Credits</Badge>}
    </div>
  );
}

// ── Right Insights Sidebar ─────────────────────────────────────────────────────

function VerificationDonut({ data }: { data: TenantsInsights["verification_overview"] }) {
  const items = [
    { label: "Not Started",       count: data.not_started,       color: "#9ca3af" },
    { label: "In Progress",       count: data.in_progress,       color: "#6366f1" },
    { label: "Completed",         count: data.completed,         color: "var(--success)" },
    { label: "Changes Requested", count: data.changes_requested, color: "var(--warning)" },
    { label: "Rejected",          count: data.rejected,          color: "var(--danger)" },
  ];
  const total = data.total || 1;
  return (
    <Card style={{ padding: "14px 16px", marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Verification Overview</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map(item => (
          <div key={item.label}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{item.label}</span>
              <span style={{ fontSize: 11, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{item.count}</span>
            </div>
            <div style={{ height: 4, background: "var(--border)", borderRadius: 2 }}>
              <div style={{ height: 4, background: item.color, borderRadius: 2, width: `${(item.count / total) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TopLocations({ data }: { data: TenantsInsights["top_locations"] }) {
  const max = Math.max(...data.map(x => x.count), 1);
  return (
    <Card style={{ padding: "14px 16px", marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Top Locations</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.map(item => (
          <div key={`${item.city}-${item.state}`} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <MapPin size={11} style={{ color: "var(--text-tertiary)", flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.city}, {item.state}</div>
              <div style={{ height: 3, background: "var(--border)", borderRadius: 2, marginTop: 2 }}>
                <div style={{ height: 3, background: "var(--brand)", borderRadius: 2, width: `${(item.count / max) * 100}%` }} />
              </div>
            </div>
            <span style={{ fontSize: 11, color: "var(--text-secondary)", flexShrink: 0 }}>{item.count}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function RecentActivity({ data }: { data: TenantsInsights["recent_activity"] }) {
  return (
    <Card style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Recent Activity</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.slice(0, 7).map((item, i) => (
          <div key={i} style={{ display: "flex", gap: 8, paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Activity size={11} style={{ color: "var(--brand)" }} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 11, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.tenant_name}</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{item.action}</div>
              <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{timeAgo(item.created_at)}</div>
            </div>
          </div>
        ))}
        {data.length === 0 && <div style={{ fontSize: 12, color: "var(--text-secondary)", textAlign: "center", padding: "8px 0" }}>No recent activity.</div>}
      </div>
    </Card>
  );
}

// ── Bottom Intelligence Cards ──────────────────────────────────────────────────

function BottomCards({ insights }: { insights: TenantsInsights }) {
  const h = insights.health_summary;
  const f = insights.financial_summary;
  const v = insights.verification_overview;

  const cardStyle: React.CSSProperties = { padding: "16px 18px", flex: "1 1 220px", minWidth: 0 };

  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 16 }}>
      {/* Onboarding Health */}
      <Card style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius:"var(--radius-md)", background: "#6366f120", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <TrendingUp size={15} style={{ color: "#6366f1" }} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 13 }}>Onboarding Health</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Completed</span>
            <span style={{ fontWeight: 600 }}>{v.completed}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Verification Pending</span>
            <span style={{ fontWeight: 600 }}>{v.in_progress + v.not_started}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Changes Requested</span>
            <span style={{ fontWeight: 600, color: "var(--warning)" }}>{v.changes_requested}</span>
          </div>
        </div>
        <Link href="/admin/tenants/onboarding" style={{ display: "inline-block", marginTop: 10, fontSize: 11, color: "var(--brand)" }}>View Onboarding →</Link>
      </Card>

      {/* Business Health */}
      <Card style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius:"var(--radius-md)", background: "var(--success)20", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <BarChart2 size={15} style={{ color: "var(--success)" }} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 13 }}>Business Health</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Avg Health Score</span>
            <span style={{ fontWeight: 700, color: "var(--success)" }}>{h.average_health_score}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>High Risk</span>
            <span style={{ fontWeight: 600, color: "var(--danger)" }}>{h.high_risk}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Medium Risk</span>
            <span style={{ fontWeight: 600, color: "var(--warning)" }}>{h.medium_risk}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Low Risk</span>
            <span style={{ fontWeight: 600, color: "var(--success)" }}>{h.low_risk}</span>
          </div>
        </div>
      </Card>

      {/* Financial Usage Summary — Usage Credits only, NOT real money */}
      <Card style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius:"var(--radius-md)", background: "var(--warning)20", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CreditCard size={15} style={{ color: "var(--warning)" }} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 13 }}>Usage Credit Summary</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Total Usage Credits</span>
            <span style={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>₹{f.total_usage_credits.toLocaleString("en-IN")}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Low Credit Providers</span>
            <span style={{ fontWeight: 600, color: f.low_credit_tenants > 0 ? "var(--danger)" : "var(--text)" }}>{f.low_credit_tenants}</span>
          </div>
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: "var(--text-tertiary)", background: "var(--surface-sunken)", padding: "4px 8px", borderRadius: 4 }}>
          Usage credits are not real money — usage-credit wallet only
        </div>
      </Card>
    </div>
  );
}

// ── Action Modals ──────────────────────────────────────────────────────────────

function AddCreditsModal({ open, tenant, onClose, onDone }: { open: boolean; tenant: TenantListItem | null; onClose: () => void; onDone: () => void }) {
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const { execute, loading, error } = useAction(async () => {
    if (!tenant) return;
    if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) throw new Error("Enter a valid amount.");
    if (!reason.trim()) throw new Error("Reason is required.");
    await adminTenantsApi.addUsageCredits(tenant.tenant_id, Number(amount), reason);
    setAmount(""); setReason(""); onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };
  return (
    <Modal open={open} title="Add Usage Credits" onClose={onClose}>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12, background: "var(--surface-sunken)", padding: "8px 12px", borderRadius: 6 }}>
        <strong>Note:</strong> Usage credits are not real money. This is a usage-credit wallet for job deductions only.
      </div>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Add usage credits for <strong>{tenant?.business_name || tenant?.tenant_name}</strong>.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8 }}>{error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Amount (₹) *</label>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)} placeholder="e.g. 1000" style={inp} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Reason *</label>
          <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. Promotional credit for new onboarding" style={inp} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" onClick={() => execute()} disabled={loading}>
          {loading ? "Adding…" : "Add Credits"}
        </Btn>
      </div>
    </Modal>
  );
}

function SuspendModal({ open, tenant, onClose, onDone }: { open: boolean; tenant: TenantListItem | null; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const { execute, loading, error } = useAction(async () => {
    if (!tenant) return;
    if (!reason.trim()) throw new Error("Reason is required.");
    await adminTenantsApi.suspend(tenant.tenant_id, reason);
    setReason(""); onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };
  return (
    <Modal open={open} title="Suspend Tenant" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Suspend <strong>{tenant?.business_name || tenant?.tenant_name}</strong>? This blocks all bookings and jobs.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8 }}>{error}</div>}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Reason *</label>
        <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. Policy violation" style={inp} />
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="danger" onClick={() => execute()} disabled={loading}>{loading ? "Suspending…" : "Suspend"}</Btn>
      </div>
    </Modal>
  );
}

function RequestChangesModal({ open, tenant, onClose, onDone }: { open: boolean; tenant: TenantListItem | null; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const { execute, loading, error } = useAction(async () => {
    if (!tenant) return;
    if (!reason.trim()) throw new Error("Reason is required.");
    await adminTenantsApi.requestChanges(tenant.tenant_id, reason);
    setReason(""); onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };
  return (
    <Modal open={open} title="Request Changes" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Request verification changes from <strong>{tenant?.business_name || tenant?.tenant_name}</strong>.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8 }}>{error}</div>}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Reason *</label>
        <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. Missing GST certificate" style={inp} />
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="warning" onClick={() => execute()} disabled={loading}>{loading ? "Sending…" : "Request Changes"}</Btn>
      </div>
    </Modal>
  );
}

function SendNotificationModal({ open, tenant, onClose, onDone }: { open: boolean; tenant: TenantListItem | null; onClose: () => void; onDone: () => void }) {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const { execute, loading, error } = useAction(async () => {
    if (!tenant) return;
    if (!message.trim()) throw new Error("Message is required.");
    await adminTenantsApi.sendNotification(tenant.tenant_id, subject, message);
    setSubject(""); setMessage(""); onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };
  return (
    <Modal open={open} title="Send Notification" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Notify <strong>{tenant?.business_name || tenant?.tenant_name}</strong>.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8 }}>{error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Subject</label>
          <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Optional subject" style={inp} />
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Message *</label>
          <textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="Enter notification message…" style={{ ...inp, height: 80, padding: "8px 10px", resize: "vertical" }} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" onClick={() => execute()} disabled={loading}>{loading ? "Sending…" : "Send"}</Btn>
      </div>
    </Modal>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

function TenantsPageInner() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage]       = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [modal, setModal]     = useState<ActiveModal>(null);

  const filtersKey = JSON.stringify({ ...filters, page });

  const { data: summaryData, refetch: reloadSummary } = useApi(
    () => adminTenantsApi.getSummary(), []
  );
  const { data: insightsData } = useApi(
    () => adminTenantsApi.getInsights(), []
  );
  const { data: listData, loading, refetch: reload } = useApi(
    () => {
      const f: Filters & { page: number } = { ...JSON.parse(filtersKey) };
      return adminTenantsApi.list({
        q: f.q || undefined,
        status: f.status || undefined,
        verification_status: f.verification_status || undefined,
        city_tier: f.city_tier || undefined,
        state: f.state || undefined,
        city: f.city || undefined,
        created_from: f.created_from || undefined,
        created_to: f.created_to || undefined,
        sort_by: f.sort_by,
        sort_direction: f.sort_dir,
        page,
        page_size: PAGE_SIZE,
      });
    },
    [filtersKey]
  );

  const refresh = useCallback(() => { reload(); reloadSummary(); setSelected(new Set()); }, [reload, reloadSummary]);
  const handleFilter = useCallback((f: Partial<Filters>) => { setFilters(p => ({ ...p, ...f })); setPage(1); }, []);

  const summary = summaryData as TenantsSummary | null;
  const insights = insightsData as TenantsInsights | null;

  const rawList = listData as { items: TenantListItem[]; pagination: { total_items: number; total_pages: number; has_next: boolean } } | null;
  const items = (rawList?.items ?? []) as Row[];
  const total = rawList?.pagination?.total_items ?? 0;
  const totalPages = rawList?.pagination?.total_pages ?? 1;

  const { execute: execReactivate } = useAction(async (t: TenantListItem) => {
    await adminTenantsApi.reactivate(t.tenant_id, "Reactivated by admin");
    refresh();
  });

  const handleRowAction = useCallback((type: string, tenant: TenantListItem) => {
    if (type === "view")    { window.location.href = `/admin/tenants/${tenant.tenant_id}`; return; }
    if (type === "360")     { window.location.href = `/admin/tenants/${tenant.tenant_id}`; return; }
    if (type === "verify")  { window.location.href = `/admin/tenants/${tenant.tenant_id}?tab=onboarding`; return; }
    if (type === "audit")   { window.location.href = `/admin/tenants/${tenant.tenant_id}?tab=audit`; return; }
    if (type === "reactivate") { execReactivate(tenant); return; }
    if (type === "add_credits")       setModal({ type: "add_credits",       tenant });
    if (type === "suspend")           setModal({ type: "suspend",           tenant });
    if (type === "request_changes")   setModal({ type: "request_changes",   tenant });
    if (type === "send_notification") setModal({ type: "send_notification", tenant });
  }, [execReactivate]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await adminTenantsApi.exportCsv({
        status: filters.status || undefined,
        verification_status: filters.verification_status || undefined,
        state: filters.state || undefined,
        city: filters.city || undefined,
        search: filters.q || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "tenants_export.csv"; a.click();
    } catch { /* silent */ }
  }, [filters]);

  const toggleSelect = (id: string) => setSelected(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  const columns: { key: string; label: string; render?: (_v: unknown, row: Row) => React.ReactNode }[] = [
    { key: "sel", label: "", render: (_v, row) => <input type="checkbox" checked={selected.has(row.tenant_id as string)} onChange={() => toggleSelect(row.tenant_id as string)} onClick={e => e.stopPropagation()} /> },
    {
      key: "tenant_name", label: "Tenant",
      render: (_v, row) => <TenantCell row={row as unknown as TenantListItem} />,
    },
    {
      key: "status", label: "Status",
      render: (_v, row) => (
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <StatusBadge status={row.status as string} size="sm" />
        </div>
      ),
    },
    {
      key: "verification_status", label: "Verification",
      render: (_v, row) => <VerifCell status={row.verification_status as string} />,
    },
    {
      key: "vertical", label: "Vertical",
      render: (_v, row) => <span style={{ fontSize: 12 }}>{VERTICAL_LABEL[row.vertical as string] || humanize(row.vertical as string || "")}</span>,
    },
    {
      key: "health_band", label: "Health",
      render: (_v, row) => {
        const score = row.health_score as number ?? 0;
        const band = row.health_band as string ?? "silver";
        const color = score >= 80 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--danger)";
        return (
          <div>
            <span style={{ fontSize: 13, fontWeight: 700, color }}>{score}</span>
            <span style={{ fontSize: 10, color: "var(--text-tertiary)", marginLeft: 4 }}>{humanize(band)}</span>
          </div>
        );
      },
    },
    {
      key: "city", label: "Location",
      render: (_v, row) => {
        const parts = [row.city, row.state].filter(Boolean) as string[];
        return <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{parts.join(", ") || "—"}</span>;
      },
    },
    {
      key: "usage_credit_balance", label: "Usage Credits",
      render: (_v, row) => <CreditsCell balance={row.usage_credit_balance as number ?? 0} />,
    },
    {
      key: "active_jobs", label: "Jobs",
      render: (_v, row) => (
        <div style={{ fontSize: 12 }}>
          <span style={{ fontWeight: 600 }}>{row.active_jobs as number ?? 0}</span>
          <span style={{ color: "var(--text-secondary)" }}> active</span>
          <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{row.completed_jobs as number ?? 0} completed</div>
        </div>
      ),
    },
    {
      key: "open_complaints", label: "Issues",
      render: (_v, row) => {
        const n = row.open_complaints as number ?? 0;
        return n > 0
          ? <Badge variant="danger" size="sm"><AlertCircle size={9} /> {n} open</Badge>
          : <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>—</span>;
      },
    },
    {
      key: "created_at", label: "Created",
      render: (_v, row) => <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{fmtDate(row.created_at as string)}</span>,
    },
    {
      key: "actions", label: "",
      render: (_v, row) => (
        <div onClick={e => e.stopPropagation()}>
          <TenantActions row={row as unknown as TenantListItem} onAction={handleRowAction} />
        </div>
      ),
    },
  ];

  return (
    <AdminLayout activeNav="tenants">
      <div style={{ padding: "28px 32px", minHeight: "100vh" }}>
        {/* Page Header */}
        <PageHeader
          title="Tenants"
          description="Manage provider businesses, verification status, usage credits, service coverage, and operational health."
          actions={
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="secondary" size="sm" onClick={handleExport}><Download size={12} /> Export</Btn>
              <Btn variant="secondary" size="sm" onClick={refresh}><RefreshCw size={12} /></Btn>
            </div>
          }
        />

        {/* KPI Cards */}
        <KpiCards s={summary} loading={!summaryData} onFilter={handleFilter} />

        {/* Main Layout: table + right sidebar */}
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          {/* Table area */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <Toolbar
              filters={filters}
              onChange={f => { setFilters(f); setPage(1); }}
              onExport={handleExport}
              onRefresh={refresh}
              onAdd={() => { window.location.href = "/admin/tenants/onboarding"; }}
            />
            {selected.size > 0 && (
              <BulkBar
                count={selected.size}
                onSuspend={() => { /* bulk suspend would need a modal */ }}
                onClear={() => setSelected(new Set())}
              />
            )}

            <Card style={{ padding: "16px 20px" }}>
              {/* Row count */}
              {!loading && total > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12, fontSize: 12, color: "var(--text-secondary)" }}>
                  <span>
                    Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString()} providers
                    {selected.size > 0 && <span style={{ marginLeft: 8, color: "var(--brand)", fontWeight: 600 }}>· {selected.size} selected</span>}
                  </span>
                  {selected.size > 0 && (
                    <Btn variant="ghost" size="sm" onClick={() => setSelected(new Set())} style={{ fontSize: 11 }}>Clear selection</Btn>
                  )}
                </div>
              )}

              {/* Loading */}
              {loading && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="skeleton" style={{ height: 56, borderRadius:"var(--radius-md)" }} />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {!loading && items.length === 0 && (
                <div style={{ textAlign: "center", padding: "56px 0" }}>
                  <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                    <Building2 size={28} style={{ color: "var(--text-tertiary)" }} />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>No tenants found</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 20, maxWidth: 400, margin: "0 auto 20px" }}>
                    {Object.values(filters).some(Boolean)
                      ? "No providers match these filters. Clear filters or broaden your search."
                      : "Invite or create your first provider business to start onboarding."}
                  </div>
                  {Object.values(filters).some(Boolean)
                    ? <Btn variant="secondary" size="sm" onClick={() => setFilters(DEFAULT_FILTERS)}>Clear Filters</Btn>
                    : <Btn variant="primary" size="sm" onClick={() => { window.location.href = "/admin/tenants/onboarding"; }}><Plus size={12} /> Add Tenant</Btn>
                  }
                </div>
              )}

              {/* Table */}
              {!loading && items.length > 0 && (
                <DataTable<Row>
                  columns={columns}
                  rows={items}
                  onRowClick={row => { window.location.href = `/admin/tenants/${(row as TenantListItem).tenant_id}`; }}
                />
              )}

              {/* Pagination */}
              <Pagination page={page} pageSize={PAGE_SIZE} total={total} pageCount={totalPages} onPage={setPage} itemLabel="providers" />
            </Card>

            {/* Bottom intelligence cards */}
            {insights && <BottomCards insights={insights} />}
          </div>

          {/* Right insight sidebar */}
          <div style={{ width: 260, flexShrink: 0 }}>
            {insights ? (
              <>
                <VerificationDonut data={insights.verification_overview} />
                <TopLocations data={insights.top_locations} />
                <RecentActivity data={insights.recent_activity} />
              </>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {[120, 160, 140, 200].map((h, i) => <div key={i} className="skeleton" style={{ height: h, borderRadius: 10 }} />)}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Modals */}
      <AddCreditsModal
        open={modal?.type === "add_credits"}
        tenant={modal?.type === "add_credits" ? modal.tenant : null}
        onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }}
      />
      <SuspendModal
        open={modal?.type === "suspend"}
        tenant={modal?.type === "suspend" ? modal.tenant : null}
        onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }}
      />
      <RequestChangesModal
        open={modal?.type === "request_changes"}
        tenant={modal?.type === "request_changes" ? modal.tenant : null}
        onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }}
      />
      <SendNotificationModal
        open={modal?.type === "send_notification"}
        tenant={modal?.type === "send_notification" ? modal.tenant : null}
        onClose={() => setModal(null)} onDone={() => { setModal(null); refresh(); }}
      />
    </AdminLayout>
  );
}

export default function AdminTenantsPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40 }}>Loading…</div>}>
      <TenantsPageInner />
    </Suspense>
  );
}
