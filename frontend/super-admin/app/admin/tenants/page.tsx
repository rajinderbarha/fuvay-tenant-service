"use client";
import React, { useState, useCallback, useRef, Suspense } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, CardHeader, SectionHeader, StatCard, Badge, Btn, Modal, DataTable,
} from "../../../components/shared/ui";
import {
  Search, RefreshCw, Users, CheckCircle, Clock, AlertCircle, XCircle,
  Download, Eye, Archive, Flag, Shield, X, Filter, ChevronDown, ChevronLeft,
  ChevronRight, Building2, UserCheck, Package, MapPin, Zap, TrendingUp,
  TrendingDown, MoreVertical, Bell, CreditCard, RotateCcw, Plus,
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
const PLAN_LABEL: Record<string, string> = {
  free: "Free", starter: "Starter", growth: "Growth",
  professional: "Professional", enterprise: "Enterprise",
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
  q: string; status: string; verification_status: string; plan_type: string;
  city_tier: string; state: string; city: string; created_from: string; created_to: string;
  sort_by: string; sort_dir: string;
}
const DEFAULT_FILTERS: Filters = {
  q: "", status: "", verification_status: "", plan_type: "",
  city_tier: "", state: "", city: "", created_from: "", created_to: "",
  sort_by: "created_at", sort_dir: "desc",
};

type ActiveModal =
  | { type: "add_credits"; tenant: TenantListItem }
  | { type: "change_plan"; tenant: TenantListItem }
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
  const v = s ?? { total: 0, active: 0, pending_review: 0, pending_setup: 0, changes_requested: 0, suspended: 0, rejected: 0, package_pending_approval: 0 };

  const cards: { label: string; value: number; accent: string; icon: React.ReactNode; filter: Partial<Filters>; alert?: boolean }[] = [
    { label: "Total Providers",       value: v.total,                     accent: "var(--brand)", icon: <Building2 />, filter: {} },
    { label: "Active",                value: v.active,                    accent: "#16a34a",     icon: <CheckCircle />, filter: { status: "active" } },
    { label: "Pending Review",        value: v.pending_review,            accent: "#d97706",     icon: <Clock />, filter: { verification_status: "pending" } },
    { label: "Pending Setup",         value: v.pending_setup,             accent: "#6366f1",     icon: <Settings />, filter: { verification_status: "not_started" } },
    { label: "Changes Requested",     value: v.changes_requested,         accent: "#0891b2",     icon: <Edit />, filter: { verification_status: "changes_requested" } },
    { label: "Suspended",             value: v.suspended,                 accent: "#dc2626",     icon: <Lock />, filter: { status: "suspended" }, alert: v.suspended > 0 },
    { label: "Rejected",              value: v.rejected,                  accent: "#9ca3af",     icon: <XCircle />, filter: { status: "rejected" } },
    { label: "Pkg Pending Approval",  value: v.package_pending_approval,  accent: "#f59e0b",     icon: <Package />, filter: {} },
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
  const [adv, setAdv] = useState(false);
  const inp: React.CSSProperties = { height: 34, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 12 };
  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...filters, [k]: e.target.value });

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 240 }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }} />
          <input
            placeholder="Search by name, email, phone, tenant ID…"
            value={filters.q} onChange={set("q")}
            style={{ ...inp, width: "100%", paddingLeft: 30 }}
          />
        </div>
        <select value={filters.status} onChange={set("status")} style={inp}>
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={filters.verification_status} onChange={set("verification_status")} style={inp}>
          <option value="">All Verification</option>
          {Object.entries(VERIF_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={filters.plan_type} onChange={set("plan_type")} style={inp}>
          <option value="">All Plans</option>
          {Object.entries(PLAN_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <Btn variant="secondary" size="sm" onClick={() => setAdv(!adv)}>
          <Filter size={12} /> Advanced {adv ? <ChevronDown size={11} style={{ transform: "rotate(180deg)" }} /> : <ChevronDown size={11} />}
        </Btn>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <Btn variant="secondary" size="sm" onClick={onExport}><Download size={12} /> Export</Btn>
          <Btn variant="secondary" size="sm" onClick={onRefresh}><RefreshCw size={12} /></Btn>
          <Btn variant="primary" size="sm" onClick={onAdd}><Plus size={12} /> Add Tenant</Btn>
        </div>
      </div>
      {adv && (
        <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap", padding: "12px 16px", background: "var(--surface-sunken)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <select value={filters.city_tier} onChange={set("city_tier")} style={inp}>
            <option value="">All Tiers</option>
            <option value="metro">Metro</option>
            <option value="large">Large City</option>
            <option value="mid">Mid-Size</option>
            <option value="small">Small Town</option>
          </select>
          <input placeholder="State" value={filters.state} onChange={set("state")} style={{ ...inp, width: 140 }} />
          <input placeholder="City" value={filters.city} onChange={set("city")} style={{ ...inp, width: 140 }} />
          <select value={filters.sort_by} onChange={set("sort_by")} style={inp}>
            <option value="created_at">Sort: Created</option>
            <option value="updated_at">Sort: Updated</option>
            <option value="tenant_name">Sort: Name</option>
            <option value="health_score">Sort: Health</option>
          </select>
          <select value={filters.sort_dir} onChange={set("sort_dir")} style={inp}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="date" value={filters.created_from} onChange={set("created_from")} style={{ ...inp, fontSize: 11 }} />
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>to</span>
            <input type="date" value={filters.created_to} onChange={set("created_to")} style={{ ...inp, fontSize: 11 }} />
          </div>
          <Btn variant="ghost" size="sm" onClick={() => { onChange(DEFAULT_FILTERS); setAdv(false); }}>Clear All</Btn>
        </div>
      )}
    </div>
  );
}

// ── Active Filter Chips ────────────────────────────────────────────────────────

function ActiveChips({ filters, onChange }: { filters: Filters; onChange: (f: Filters) => void }) {
  const chips: { key: keyof Filters; label: string }[] = [];
  if (filters.q)                    chips.push({ key: "q",                    label: `"${filters.q}"` });
  if (filters.status)               chips.push({ key: "status",               label: STATUS_LABEL[filters.status] || filters.status });
  if (filters.verification_status)  chips.push({ key: "verification_status",  label: `Verif: ${VERIF_LABEL[filters.verification_status] || filters.verification_status}` });
  if (filters.plan_type)            chips.push({ key: "plan_type",            label: `Plan: ${PLAN_LABEL[filters.plan_type] || filters.plan_type}` });
  if (filters.city_tier)            chips.push({ key: "city_tier",            label: `Tier: ${humanize(filters.city_tier)}` });
  if (filters.state)                chips.push({ key: "state",                label: `State: ${filters.state}` });
  if (filters.city)                 chips.push({ key: "city",                 label: `City: ${filters.city}` });
  if (filters.created_from)         chips.push({ key: "created_from",         label: `From: ${filters.created_from}` });
  if (filters.created_to)           chips.push({ key: "created_to",           label: `To: ${filters.created_to}` });
  if (!chips.length) return null;
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
      {chips.map(c => (
        <span key={c.key} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, background: "var(--accent-muted, #eff6ff)", color: "var(--accent, #2563eb)", border: "1px solid var(--border)", borderRadius: 999, padding: "2px 10px" }}>
          {c.label}
          <button onClick={() => onChange({ ...filters, [c.key]: "" })} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", padding: 0, lineHeight: 1 }}><X size={10} /></button>
        </span>
      ))}
      <Btn variant="ghost" size="sm" onClick={() => onChange(DEFAULT_FILTERS)} style={{ fontSize: 11 }}>Clear all</Btn>
    </div>
  );
}

// ── Bulk Action Bar ────────────────────────────────────────────────────────────

function BulkBar({ count, onSuspend, onClear }: { count: number; onSuspend: () => void; onClear: () => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", background: "var(--accent-muted, #eff6ff)", border: "1px solid var(--border)", borderRadius: 8, marginBottom: 12 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent, #2563eb)" }}>{count} selected</span>
      <Btn variant="danger" size="sm" onClick={onSuspend}><Lock size={12} /> Suspend All</Btn>
      <button onClick={onClear} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}><X size={14} /></button>
    </div>
  );
}

// ── Row Action Menu ────────────────────────────────────────────────────────────

function RowActions({ row, onAction }: {
  row: TenantListItem;
  onAction: (type: string, tenant: TenantListItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const items: { label: string; icon: React.ReactNode; action: string; danger?: boolean; divider?: boolean }[] = [
    { label: "View Details",       icon: <Eye size={12} />,        action: "view" },
    { label: "Open 360",           icon: <ExternalLink size={12} />, action: "360" },
    { label: "—", icon: null, action: "", divider: true },
    { label: "Review Verification",icon: <UserCheck size={12} />,  action: "verify" },
    { label: "Request Changes",    icon: <Edit size={12} />,       action: "request_changes" },
    { label: "Change Plan",        icon: <Package size={12} />,    action: "change_plan" },
    { label: "Add Usage Credits",  icon: <CreditCard size={12} />, action: "add_credits" },
    { label: "—", icon: null, action: "", divider: true },
    { label: "Send Notification",  icon: <Bell size={12} />,       action: "send_notification" },
    { label: "View Audit Logs",    icon: <Activity size={12} />,   action: "audit" },
    { label: "—", icon: null, action: "", divider: true },
    ...(row.status !== "suspended"
      ? [{ label: "Suspend Tenant", icon: <Lock size={12} />, action: "suspend", danger: true }]
      : [{ label: "Reactivate",     icon: <RotateCcw size={12} />, action: "reactivate" }]
    ),
  ];

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <Btn variant="ghost" size="sm" onClick={() => setOpen(!open)} style={{ padding: "4px 8px" }}>
        <MoreVertical size={13} />
      </Btn>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setOpen(false)} />
          <div style={{ position: "absolute", right: 0, top: "100%", zIndex: 50, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,.12)", minWidth: 200, padding: "4px 0", marginTop: 4 }}>
            {items.map((item, i) => item.divider
              ? <div key={i} style={{ height: 1, background: "var(--border)", margin: "4px 0" }} />
              : (
                <button key={item.action} onClick={() => { setOpen(false); onAction(item.action, row); }}
                  style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 14px", background: "none", border: "none", cursor: "pointer", fontSize: 12, color: item.danger ? "#dc2626" : "var(--text)", textAlign: "left" }}>
                  <span style={{ color: item.danger ? "#dc2626" : "var(--text-secondary)" }}>{item.icon}</span>
                  {item.label}
                </button>
              )
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Verification Progress Cell ─────────────────────────────────────────────────

function VerifCell({ status }: { status: string }) {
  const v = VERIF_V[status] ?? "muted";
  const l = VERIF_LABEL[status] ?? humanize(status);
  return (
    <div>
      <Badge variant={v} size="sm">{l}</Badge>
    </div>
  );
}

// ── Tenant Name Cell ───────────────────────────────────────────────────────────

function TenantCell({ row }: { row: TenantListItem }) {
  const initials = (row.business_name || row.tenant_name || "?").slice(0, 2).toUpperCase();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--brand)20", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13, color: "var(--brand)", flexShrink: 0 }}>
        {row.logo_url
          ? <img src={row.logo_url} alt="" style={{ width: 36, height: 36, borderRadius: 8, objectFit: "cover" }} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
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
      <div style={{ fontSize: 13, fontWeight: 600, fontVariantNumeric: "tabular-nums", color: low ? "#dc2626" : "var(--text)" }}>
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
    { label: "Completed",         count: data.completed,         color: "#16a34a" },
    { label: "Changes Requested", count: data.changes_requested, color: "#f59e0b" },
    { label: "Rejected",          count: data.rejected,          color: "#dc2626" },
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

function PlanDistribution({ data }: { data: TenantsInsights["plan_distribution"] }) {
  const total = data.reduce((s, x) => s + x.count, 0) || 1;
  const colors: Record<string, string> = { enterprise: "#6366f1", professional: "#8b5cf6", growth: "#0891b2", starter: "#16a34a", free: "#9ca3af" };
  return (
    <Card style={{ padding: "14px 16px", marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Plan Distribution</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {data.map(item => (
          <div key={item.plan}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{PLAN_LABEL[item.plan] || humanize(item.plan)}</span>
              <span style={{ fontSize: 11, fontWeight: 600 }}>{item.count}</span>
            </div>
            <div style={{ height: 4, background: "var(--border)", borderRadius: 2 }}>
              <div style={{ height: 4, background: colors[item.plan] || "#6366f1", borderRadius: 2, width: `${(item.count / total) * 100}%` }} />
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
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#6366f120", display: "flex", alignItems: "center", justifyContent: "center" }}>
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
            <span style={{ fontWeight: 600, color: "#f59e0b" }}>{v.changes_requested}</span>
          </div>
        </div>
        <a href="/admin/tenants/onboarding" style={{ display: "inline-block", marginTop: 10, fontSize: 11, color: "var(--brand)" }}>View Onboarding →</a>
      </Card>

      {/* Business Health */}
      <Card style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#16a34a20", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <BarChart2 size={15} style={{ color: "#16a34a" }} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 13 }}>Business Health</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Avg Health Score</span>
            <span style={{ fontWeight: 700, color: "#16a34a" }}>{h.average_health_score}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>High Risk</span>
            <span style={{ fontWeight: 600, color: "#dc2626" }}>{h.high_risk}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Medium Risk</span>
            <span style={{ fontWeight: 600, color: "#f59e0b" }}>{h.medium_risk}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Low Risk</span>
            <span style={{ fontWeight: 600, color: "#16a34a" }}>{h.low_risk}</span>
          </div>
        </div>
      </Card>

      {/* Financial Usage Summary — Usage Credits only, NOT real money */}
      <Card style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#f59e0b20", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CreditCard size={15} style={{ color: "#f59e0b" }} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 13 }}>Usage Credit Summary</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Total Usage Credits</span>
            <span style={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>₹{f.total_usage_credits.toLocaleString("en-IN")}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Security Deposits</span>
            <span style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>₹{f.total_security_deposits.toLocaleString("en-IN")}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>Low Credit Providers</span>
            <span style={{ fontWeight: 600, color: f.low_credit_tenants > 0 ? "#dc2626" : "var(--text)" }}>{f.low_credit_tenants}</span>
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

function ChangePlanModal({ open, tenant, onClose, onDone }: { open: boolean; tenant: TenantListItem | null; onClose: () => void; onDone: () => void }) {
  const [plan, setPlan] = useState("");
  const [reason, setReason] = useState("");
  const { execute, loading, error } = useAction(async () => {
    if (!tenant) return;
    if (!plan) throw new Error("Select a plan.");
    if (!reason.trim()) throw new Error("Reason is required.");
    await adminTenantsApi.changePlan(tenant.tenant_id, plan, reason);
    setPlan(""); setReason(""); onDone();
  });
  const inp: React.CSSProperties = { width: "100%", height: 36, border: "1px solid var(--border)", borderRadius: 6, padding: "0 10px", background: "var(--surface)", color: "var(--text)", fontSize: 13 };
  return (
    <Modal open={open} title="Change Plan" onClose={onClose}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Change plan for <strong>{tenant?.business_name || tenant?.tenant_name}</strong>.</p>
      {error && <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8 }}>{error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>New Plan *</label>
          <select value={plan} onChange={e => setPlan(e.target.value)} style={inp}>
            <option value="">Select plan…</option>
            {Object.entries(PLAN_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Reason *</label>
          <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. Upgraded by sales team" style={inp} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" onClick={() => execute()} disabled={loading}>{loading ? "Saving…" : "Change Plan"}</Btn>
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
        plan_type: f.plan_type || undefined,
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
    if (type === "change_plan")       setModal({ type: "change_plan",       tenant });
    if (type === "suspend")           setModal({ type: "suspend",           tenant });
    if (type === "request_changes")   setModal({ type: "request_changes",   tenant });
    if (type === "send_notification") setModal({ type: "send_notification", tenant });
  }, [execReactivate]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await adminTenantsApi.exportCsv({
        status: filters.status || undefined,
        verification_status: filters.verification_status || undefined,
        plan_type: filters.plan_type || undefined,
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
          <Badge variant={STATUS_V[row.status as string] ?? "muted"} size="sm">
            {STATUS_LABEL[row.status as string] || humanize(row.status as string)}
          </Badge>
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
      key: "plan_type", label: "Plan",
      render: (_v, row) => (
        <div>
          <Badge variant="muted" size="sm">{PLAN_LABEL[row.plan_type as string] || humanize(row.plan_type as string || "")}</Badge>
          <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2 }}>{humanize(row.billing_cycle as string || "monthly")}</div>
        </div>
      ),
    },
    {
      key: "health_band", label: "Health",
      render: (_v, row) => {
        const score = row.health_score as number ?? 0;
        const band = row.health_band as string ?? "silver";
        const color = score >= 80 ? "#16a34a" : score >= 60 ? "#f59e0b" : "#dc2626";
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
          <RowActions row={row as unknown as TenantListItem} onAction={handleRowAction} />
        </div>
      ),
    },
  ];

  return (
    <AdminLayout activeNav="tenants">
      <div style={{ padding: "28px 32px", minHeight: "100vh" }}>
        {/* Page Header */}
        <SectionHeader
          title="Tenants"
          subtitle="Manage provider businesses, verification status, plans, credits, service coverage, and operational health."
          icon={<Building2 />}
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
            <ActiveChips filters={filters} onChange={f => { setFilters(f); setPage(1); }} />

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
                    <div key={i} className="skeleton" style={{ height: 56, borderRadius: 8 }} />
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
              {totalPages > 1 && (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Page {page} of {totalPages}</span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Btn variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={13} /></Btn>
                    <Btn variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}><ChevronRight size={13} /></Btn>
                  </div>
                </div>
              )}
            </Card>

            {/* Bottom intelligence cards */}
            {insights && <BottomCards insights={insights} />}
          </div>

          {/* Right insight sidebar */}
          <div style={{ width: 260, flexShrink: 0 }}>
            {insights ? (
              <>
                <VerificationDonut data={insights.verification_overview} />
                <PlanDistribution data={insights.plan_distribution} />
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
      <ChangePlanModal
        open={modal?.type === "change_plan"}
        tenant={modal?.type === "change_plan" ? modal.tenant : null}
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
