"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, Input, Select, SectionHeader, DataTable, Modal,
  SummaryCard, KpiGrid, Pagination,
} from "../../../components/shared/ui";
import { ActionMenu } from "../../../components/shared/layout";
import {
  adminCustomersApi,
  AdminCustomer,
  AdminCustomerSummary,
  AdminCustomerFilterOptions,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  Search, Filter, Download, RefreshCw, ExternalLink,
  ChevronDown, X, Users, AlertTriangle, Clock, Star,
} from "lucide-react";
import Link from "next/link";
import OperationsDirectoryControls from "../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../components/enterprise/EnterpriseColumnManager";

// ── Health band config ────────────────────────────────────────────────────────
const HEALTH_BANDS = [
  { value: "",               label: "All Bands" },
  { value: "new",            label: "New" },
  { value: "healthy",        label: "Healthy" },
  { value: "active",         label: "Active" },
  { value: "at_risk",        label: "At Risk" },
  { value: "dormant",        label: "Dormant" },
  { value: "complaint_risk", label: "Complaint Risk" },
  { value: "blocked",        label: "Blocked" },
];

const HEALTH_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  new:            "muted",
  healthy:        "success",
  active:         "info",
  at_risk:        "warning",
  dormant:        "muted",
  complaint_risk: "danger",
  blocked:        "danger",
};

// ── Searchable dropdown (self-contained) ──────────────────────────────────────
interface SDProps {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  loading?: boolean;
  allLabel?: string;
  minWidth?: number;
}
function SearchDropdown({
  label, value, onChange, options,
  placeholder = "Search…", loading, allLabel = "All", minWidth = 160,
}: SDProps) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const filtered = q
    ? options.filter(o => o.label.toLowerCase().includes(q.toLowerCase()))
    : options;

  const selected = options.find(o => o.value === value);

  function pick(v: string) { onChange(v); setOpen(false); setQ(""); }

  return (
    <div ref={ref} style={{ position: "relative", minWidth }}>
      {label && (
        <div style={{ fontSize: 12, fontWeight: 500, color: "var(--muted-text)", marginBottom: 4 }}>
          {label}
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "7px 10px", border: "1px solid var(--border)", borderRadius: 6,
          background: "var(--input-bg,var(--card-bg))", color: "var(--text)",
          fontSize: 13, cursor: "pointer", gap: 6,
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, textAlign: "left" }}>
          {loading ? "Loading…" : (selected ? selected.label : allLabel)}
        </span>
        <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
          {value && (
            <span
              onClick={e => { e.stopPropagation(); onChange(""); setQ(""); }}
              style={{ color: "var(--muted-text)", cursor: "pointer", lineHeight: 1 }}
            >
              <X size={12} />
            </span>
          )}
          <ChevronDown size={13} style={{ color: "var(--muted-text)", transform: open ? "rotate(180deg)" : "none", transition: "transform .15s" }} />
        </div>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 300,
          background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,.12)", overflow: "hidden",
        }}>
          <div style={{ padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>
            <input
              autoFocus value={q} onChange={e => setQ(e.target.value)}
              placeholder={placeholder}
              style={{ width: "100%", border: "none", outline: "none", fontSize: 13, background: "transparent", color: "var(--text)" }}
            />
          </div>
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            <div
              onClick={() => pick("")}
              style={{
                padding: "7px 12px", fontSize: 13, cursor: "pointer",
                color: !value ? "var(--primary)" : "var(--muted-text)",
                background: !value ? "var(--primary-bg,rgba(242,153,74,.06))" : "transparent",
              }}
            >
              {allLabel}
            </div>
            {filtered.length === 0
              ? <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--muted-text)" }}>No results</div>
              : filtered.map(o => (
                <div key={o.value} onClick={() => pick(o.value)} style={{
                  padding: "7px 12px", fontSize: 13, cursor: "pointer",
                  color: value === o.value ? "var(--primary)" : "var(--text)",
                  fontWeight: value === o.value ? 600 : 400,
                  background: value === o.value ? "var(--primary-bg,rgba(242,153,74,.06))" : "transparent",
                }}>
                  {o.label}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Filter chip ───────────────────────────────────────────────────────────────
function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: "var(--primary-bg,rgba(242,153,74,.1))", color: "var(--primary)",
      border: "1px solid var(--primary)", borderRadius: 999,
      padding: "3px 10px", fontSize: 12, fontWeight: 500,
    }}>
      {label}
      <span onClick={onRemove} style={{ cursor: "pointer", lineHeight: 1, marginLeft: 2 }}>
        <X size={11} />
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function AdminCustomersPage() {
  return (
    <AdminLayout activeNav="customers">
      <SectionHeader
        eyebrow="Operations control plane"
        context="Customers"
        title="Customers"
        subtitle="Platform-wide customer management and engagement monitoring."
      />
      <CustomersContent />
    </AdminLayout>
  );
}

function CustomersContent() {
  const [columnState, setColumnState] = useState<ColumnDef[]>([
    { key: "full_name", label: "Customer", visible: true, order: 0 },
    { key: "phone", label: "Contact", visible: true, order: 1 },
    { key: "city", label: "Location", visible: true, order: 2 },
    { key: "health_band", label: "Health", visible: true, order: 3 },
    { key: "total_bookings", label: "Bookings", visible: true, order: 4 },
    { key: "last_tenant_name", label: "Last provider", visible: true, order: 5 },
    { key: "complaints_count", label: "Issues", visible: true, order: 6 },
    { key: "last_booking_at", label: "Last booking", visible: true, order: 7 },
    { key: "id", label: "Open", visible: true, order: 8 },
    { key: "actions", label: "Actions", visible: true, order: 9 },
  ]);
  // Draft filter state (toolbar inputs)
  const [q, setQ]             = useState("");
  const [healthBand, setHealthBand] = useState("");
  const [engagementStatus, setEngagementStatus] = useState("");
  const [bookingCountMin, setBookingCountMin] = useState("");
  const [city, setCity]       = useState("");
  const [state, setState]     = useState("");
  const [tenantId, setTenantId] = useState("");
  const [hasComplaints, setHasComplaints] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo]   = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [actionModal, setActionModal] = useState<null | { customerId: string; type: "block" | "unblock" | "suspend" | "reactivate" }>(null);
  const [actionReason, setActionReason] = useState("");

  // Applied state (triggers API)
  const [applied, setApplied] = useState({
    q: "", healthBand: "", engagementStatus: "", bookingCountMin: "", city: "", state: "", tenantId: "",
    hasComplaints: "", dateFrom: "", dateTo: "", page: 1,
  });

  // Filter options from backend
  const filtersFetch = useApi(useCallback(() => adminCustomersApi.filterOptions(), []));
  const filterOpts: AdminCustomerFilterOptions | null =
    (filtersFetch.data as { data?: AdminCustomerFilterOptions } | null)?.data ?? null;

  // Summary
  const summaryFetch = useApi(useCallback(() => adminCustomersApi.summary(), []));
  const summary: AdminCustomerSummary | null =
    (summaryFetch.data as { data?: AdminCustomerSummary } | null)?.data ?? null;

  // Customer list
  const listFetch = useApi(useCallback(() => adminCustomersApi.list({
    q:               applied.q        || undefined,
    health_band:     applied.healthBand || undefined,
    engagement_status: applied.engagementStatus || undefined,
    booking_count_min: applied.bookingCountMin ? Number(applied.bookingCountMin) : undefined,
    city:            applied.city      || undefined,
    state:           applied.state     || undefined,
    tenant_id:       applied.tenantId  || undefined,
    has_complaints:  applied.hasComplaints === "yes" ? true
                     : applied.hasComplaints === "no" ? false : undefined,
    last_booking_from: applied.dateFrom || undefined,
    last_booking_to:   applied.dateTo   || undefined,
    page:            applied.page,
    page_size:       25,
    sort_by:         "created_at",
    sort_dir:        "desc",
  }), [applied]), [applied]);

  type ListData = { customers: AdminCustomer[]; meta: { page: number; total: number; total_pages: number } };
  const listData: ListData | undefined =
    (listFetch.data as { data?: ListData } | null)?.data;
  const customers = listData?.customers ?? [];
  const meta = listData?.meta;

  function applyFilters() {
    setApplied({ q, healthBand, engagementStatus, bookingCountMin, city, state, tenantId, hasComplaints, dateFrom, dateTo, page: 1 });
  }

  function resetFilters() {
    setQ(""); setHealthBand(""); setEngagementStatus(""); setBookingCountMin(""); setCity(""); setState("");
    setTenantId(""); setHasComplaints(""); setDateFrom(""); setDateTo("");
    setApplied({ q: "", healthBand: "", engagementStatus: "", bookingCountMin: "", city: "", state: "", tenantId: "", hasComplaints: "", dateFrom: "", dateTo: "", page: 1 });
  }

  function goToPage(p: number) { setApplied(prev => ({ ...prev, page: p })); }

  function applyHealthBand(band: string) {
    const next = band === applied.healthBand ? "" : band;
    setHealthBand(next);
    setApplied(prev => ({ ...prev, healthBand: next, page: 1 }));
  }

  function applySavedView(viewFilters: Record<string, unknown>) {
    const next = {
      q: String(viewFilters.q ?? viewFilters.search ?? ""), healthBand: String(viewFilters.health_band ?? ""),
      engagementStatus: String(viewFilters.engagement_status ?? ""), bookingCountMin: String(viewFilters.booking_count_min ?? ""),
      city: String(viewFilters.city ?? ""), state: String(viewFilters.state ?? ""), tenantId: String(viewFilters.tenant_id ?? ""),
      hasComplaints: viewFilters.has_complaints === true || viewFilters.has_complaints === "true" ? "yes" : viewFilters.has_complaints === false || viewFilters.has_complaints === "false" ? "no" : "",
      dateFrom: String(viewFilters.last_booking_from ?? ""), dateTo: String(viewFilters.last_booking_to ?? ""), page: 1,
    };
    setQ(next.q); setHealthBand(next.healthBand); setEngagementStatus(next.engagementStatus);
    setBookingCountMin(next.bookingCountMin); setCity(next.city); setState(next.state);
    setTenantId(next.tenantId); setHasComplaints(next.hasComplaints); setDateFrom(next.dateFrom); setDateTo(next.dateTo);
    setApplied(next);
  }

  function applySummaryFilter(update: Partial<typeof applied>) {
    setApplied(prev => ({ ...prev, ...update, page: 1 }));
  }

  const blockAction = useAction(useCallback((id: string, r: string) => adminCustomersApi.block(id, r), []));
  const unblockAction = useAction(useCallback((id: string, r: string) => adminCustomersApi.unblock(id, r), []));
  const suspendAction = useAction(useCallback((id: string, r: string) => adminCustomersApi.suspend(id, r), []));
  const reactivateAction = useAction(useCallback((id: string, r: string) => adminCustomersApi.reactivate(id, r), []));

  async function confirmAction() {
    if (!actionModal || !actionReason) return;
    const map = { block: blockAction, unblock: unblockAction, suspend: suspendAction, reactivate: reactivateAction };
    const result = await map[actionModal.type].execute(actionModal.customerId, actionReason);
    if (result) {
      setActionModal(null); setActionReason("");
      listFetch.refetch(); summaryFetch.refetch();
    }
  }

  function exportCsv() {
    const params: Record<string, string> = {};
    if (applied.q)         params.q           = applied.q;
    if (applied.healthBand) params.health_band = applied.healthBand;
    if (applied.engagementStatus) params.engagement_status = applied.engagementStatus;
    if (applied.bookingCountMin) params.booking_count_min = applied.bookingCountMin;
    if (applied.city)      params.city         = applied.city;
    if (applied.state)     params.state        = applied.state;
    if (applied.tenantId)  params.tenant_id    = applied.tenantId;
    if (applied.hasComplaints === "yes") params.has_complaints = "true";
    if (applied.dateFrom)  params.last_booking_from = applied.dateFrom;
    if (applied.dateTo)    params.last_booking_to   = applied.dateTo;
    const path = adminCustomersApi.export(params);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = (typeof window !== "undefined" ? localStorage.getItem("serviceos_admin_token") : null) ?? "";
    fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(`Export failed (${r.status})`); return r.blob(); })
      .then(blob => {
        const a = document.createElement("a");
        const url = URL.createObjectURL(blob);
        a.href = url;
        a.download = `customers-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }).catch(() => window.alert("Customer export failed. Please try again."));
  }

  const hasFilters = !!(applied.q || applied.healthBand || applied.engagementStatus || applied.bookingCountMin || applied.city || applied.state ||
    applied.tenantId || applied.hasComplaints || applied.dateFrom || applied.dateTo);

  const advancedActiveCount = [applied.city, applied.state, applied.tenantId, applied.hasComplaints, applied.dateFrom, applied.dateTo]
    .filter(Boolean).length;

  // Table columns
  const columns = [
    {
      key: "full_name", label: "Customer",
      render: (_: unknown, row: AdminCustomer) => (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Link
            href={`/admin/customers/${row.id}`}
            style={{ fontWeight: 600, fontSize: 13, color: "var(--primary)", textDecoration: "none" }}
          >
            {row.full_name || "—"}
          </Link>
          {!row.is_active && (
            <Badge variant="danger" size="sm">Inactive</Badge>
          )}
        </div>
      ),
    },
    {
      key: "phone", label: "Contact",
      render: (_: unknown, row: AdminCustomer) => (
        <div>
          <div style={{ fontSize: 12, color: "var(--text)" }}>{row.phone || "—"}</div>
          {row.email && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.email}</div>}
        </div>
      ),
    },
    {
      key: "city", label: "Location",
      render: (_: unknown, row: AdminCustomer) => (
        <div style={{ fontSize: 12 }}>
          <div>{[row.city, row.state].filter(Boolean).join(", ") || "—"}</div>
          {row.zipcode && <div style={{ color: "var(--muted-text)", fontSize: 11 }}>{row.zipcode}</div>}
        </div>
      ),
    },
    {
      key: "health_band", label: "Health", width: 130,
      render: (_: unknown, row: AdminCustomer) => (
        <Badge variant={HEALTH_BADGE[row.health_band] ?? "muted"}>
          {row.health_band.replace(/_/g, " ")}
        </Badge>
      ),
    },
    {
      key: "total_bookings", label: "Bookings", width: 90,
      render: (_: unknown, row: AdminCustomer) => (
        <div style={{ textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{row.total_bookings}</div>
          <div style={{ fontSize: 10, color: "var(--muted-text)" }}>
            {row.completed_bookings}✓ {row.cancelled_bookings > 0 ? `${row.cancelled_bookings}✗` : ""}
          </div>
        </div>
      ),
    },
    {
      key: "last_tenant_name", label: "Last Provider",
      render: (_: unknown, row: AdminCustomer) => (
        <div style={{ fontSize: 12 }}>
          <div>{row.last_tenant_name || "—"}</div>
          {row.tenant_count > 1 && (
            <div style={{ color: "var(--muted-text)", fontSize: 11 }}>{row.tenant_count} providers</div>
          )}
        </div>
      ),
    },
    {
      key: "complaints_count", label: "Issues", width: 80,
      render: (_: unknown, row: AdminCustomer) => (
        <div style={{ textAlign: "center", fontSize: 12 }}>
          {row.complaints_count > 0
            ? <span style={{ color: "var(--danger-text,#b91c1c)", fontWeight: 600 }}>{row.complaints_count} complaint{row.complaints_count > 1 ? "s" : ""}</span>
            : <span style={{ color: "var(--muted-text)" }}>—</span>}
          {row.average_rating != null && (
            <div style={{ color: "var(--muted-text)" }}>★ {row.average_rating.toFixed(1)}</div>
          )}
        </div>
      ),
    },
    {
      key: "last_booking_at", label: "Last Booking", width: 110,
      render: (_: unknown, row: AdminCustomer) => {
        const d = row.last_booking_at ? new Date(row.last_booking_at) : null;
        return <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{d ? d.toLocaleDateString("en-IN") : "Never"}</span>;
      },
    },
    {
      key: "id", label: "", width: 36,
      render: (_: unknown, row: AdminCustomer) => (
        <Link href={`/admin/customers/${row.id}`} style={{ color: "var(--muted-text)" }}>
          <ExternalLink size={14} />
        </Link>
      ),
    },
    {
      key: "actions", label: "", width: 44,
      render: (_: unknown, row: AdminCustomer) => (
        <ActionMenu items={[
          { label: "View Customer", onClick: () => { window.location.href = `/admin/customers/${row.id}`; } },
          row.account_status === "locked"
            ? { label: "Unblock Customer", onClick: () => setActionModal({ customerId: row.id, type: "unblock" }) }
            : row.account_status === "active"
              ? { label: "Block Customer", onClick: () => setActionModal({ customerId: row.id, type: "block" }), destructive: true }
              : null,
          row.account_status === "active"
            ? { label: "Suspend Customer", onClick: () => setActionModal({ customerId: row.id, type: "suspend" }), destructive: true }
            : null,
          ["suspended", "disabled"].includes(row.account_status)
            ? { label: "Reactivate Customer", onClick: () => setActionModal({ customerId: row.id, type: "reactivate" }) }
            : null,
        ].filter(Boolean) as Parameters<typeof ActionMenu>[0]["items"]} />
      ),
    },
  ];
  const visibleKeys = new Set(columnState.filter(c => c.visible).sort((a, b) => a.order - b.order).map(c => c.key));
  const visibleColumns = columns.filter(column => visibleKeys.has(column.key));
  const enterpriseFilters: Record<string, unknown> = {
    ...(applied.q ? { q: applied.q } : {}), ...(applied.healthBand ? { health_band: applied.healthBand } : {}),
    ...(applied.engagementStatus ? { engagement_status: applied.engagementStatus } : {}),
    ...(applied.bookingCountMin ? { booking_count_min: Number(applied.bookingCountMin) } : {}),
    ...(applied.city ? { city: applied.city } : {}), ...(applied.state ? { state: applied.state } : {}),
    ...(applied.tenantId ? { tenant_id: applied.tenantId } : {}),
    ...(applied.hasComplaints ? { has_complaints: applied.hasComplaints === "yes" } : {}),
    ...(applied.dateFrom ? { last_booking_from: applied.dateFrom } : {}),
    ...(applied.dateTo ? { last_booking_to: applied.dateTo } : {}),
  };

  return (
    <div className="operations-admin-page" style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Summary cards */}
      <KpiGrid minCardWidth={150}>
        {summaryFetch.loading ? (
          <div style={{ color: "var(--muted-text)", fontSize: 13 }}>Loading summary…</div>
        ) : summary ? (
          <>
            <SummaryCard label="Total" value={summary.total.toLocaleString()} />
            <SummaryCard label="Today" value={summary.today} />
            <SummaryCard label="Active" value={summary.active} accent="var(--primary)" onClick={() => {
              const next = applied.engagementStatus === "active" ? "" : "active";
              setEngagementStatus(next); setHealthBand(""); applySummaryFilter({ engagementStatus: next, healthBand: "" });
            }} active={applied.engagementStatus === "active"} />
            <SummaryCard label="New" value={summary.new_customers} accent="var(--success-text,var(--success))" onClick={() => applyHealthBand("new")} active={applied.healthBand === "new"} />
            <SummaryCard label="Repeat Customers" value={summary.repeat_customers} onClick={() => {
              const next = applied.bookingCountMin === "2" ? "" : "2";
              setBookingCountMin(next); applySummaryFilter({ bookingCountMin: next });
            }} active={applied.bookingCountMin === "2"} />
            <SummaryCard label="At Risk" value={summary.at_risk} accent="var(--warning-text,#b45309)" onClick={() => applyHealthBand("at_risk")} active={applied.healthBand === "at_risk"} />
            <SummaryCard label="Dormant" value={summary.dormant} accent="var(--muted-text)" onClick={() => applyHealthBand("dormant")} active={applied.healthBand === "dormant"} />
            <SummaryCard label="Open Complaints" value={summary.has_complaints} accent="var(--danger-text,#b91c1c)" onClick={() => {
              const next = applied.hasComplaints === "yes" ? "" : "yes";
              setHasComplaints(next); applySummaryFilter({ hasComplaints: next });
            }} active={applied.hasComplaints === "yes"} />
            <SummaryCard label="Blocked" value={summary.blocked} accent="var(--danger-text,#b91c1c)" onClick={() => applyHealthBand("blocked")} active={applied.healthBand === "blocked"} />
            {summary.avg_rating != null && (
              <SummaryCard label="Avg Rating" value={`★ ${summary.avg_rating.toFixed(1)}`} />
            )}
            <SummaryCard label="Bkgs/Customer" value={summary.bookings_per_customer} />
          </>
        ) : null}
      </KpiGrid>

      {/* Toolbar */}
      <OperationsDirectoryControls
        resourceKey="admin_customers" filters={enterpriseFilters}
        sort={{ sort_by: "created_at", sort_direction: "desc" }} columns={columnState}
        onApplyView={applySavedView} onColumnsChange={setColumnState}
      />
      <Card padding={14}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 2, minWidth: 220 }}>
            <Input
              label=""
              placeholder="Search name, phone, email…"
              value={q}
              onChange={setQ}
            />
          </div>
          <div style={{ minWidth: 170 }}>
            <Select
              label=""
              value={healthBand}
              onChange={setHealthBand}
              options={HEALTH_BANDS}
              placeholder="All Health Bands"
            />
          </div>
          <Btn variant="secondary" size="sm" onClick={() => setShowAdvanced(!showAdvanced)}>
            <Filter size={14} style={{ marginRight: 4 }} />
            Filters
            {advancedActiveCount > 0 && (
              <span style={{
                marginLeft: 5, background: "var(--primary)", color: "#fff",
                borderRadius: 999, fontSize: 10, fontWeight: 700, padding: "1px 5px",
              }}>
                {advancedActiveCount}
              </span>
            )}
          </Btn>
          <Btn variant="primary" size="sm" onClick={applyFilters}>
            <Search size={14} style={{ marginRight: 4 }} />Search
          </Btn>
          {hasFilters && <Btn variant="ghost" size="sm" onClick={resetFilters}>Clear</Btn>}
          <Btn variant="ghost" size="sm" onClick={() => { listFetch.refetch(); summaryFetch.refetch(); }}>
            <RefreshCw size={14} style={{ marginRight: 4 }} />Refresh
          </Btn>
          <Btn variant="ghost" size="sm" onClick={exportCsv}>
            <Download size={14} style={{ marginRight: 4 }} />CSV
          </Btn>
        </div>

        {/* Advanced filters */}
        {showAdvanced && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <SearchDropdown
              label="City"
              value={city}
              onChange={setCity}
              options={filterOpts?.cities ?? []}
              placeholder="Search cities…"
              loading={filtersFetch.loading}
              allLabel="All Cities"
            />
            <SearchDropdown
              label="State"
              value={state}
              onChange={setState}
              options={filterOpts?.states ?? []}
              placeholder="Search states…"
              loading={filtersFetch.loading}
              allLabel="All States"
            />
            <SearchDropdown
              label="Provider"
              value={tenantId}
              onChange={setTenantId}
              options={filterOpts?.tenants ?? []}
              placeholder="Search providers…"
              loading={filtersFetch.loading}
              allLabel="All Providers"
              minWidth={210}
            />
            <div style={{ minWidth: 150 }}>
              <Select
                label="Has Complaints"
                value={hasComplaints}
                onChange={setHasComplaints}
                options={[{ value: "", label: "Any" }, { value: "yes", label: "Yes" }, { value: "no", label: "No" }]}
                placeholder="Any"
              />
            </div>
            <div style={{ minWidth: 140 }}>
              <Input label="Last Booking From" placeholder="YYYY-MM-DD" value={dateFrom} onChange={setDateFrom} />
            </div>
            <div style={{ minWidth: 140 }}>
              <Input label="Last Booking To" placeholder="YYYY-MM-DD" value={dateTo} onChange={setDateTo} />
            </div>
          </div>
        )}

        {/* Active filter chips */}
        {hasFilters && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
            {applied.healthBand && <FilterChip label={`Health: ${applied.healthBand.replace(/_/g, " ")}`} onRemove={() => { setHealthBand(""); setApplied(p => ({ ...p, healthBand: "", page: 1 })); }} />}
            {applied.engagementStatus && <FilterChip label="Active customers" onRemove={() => { setEngagementStatus(""); setApplied(p => ({ ...p, engagementStatus: "", page: 1 })); }} />}
            {applied.bookingCountMin && <FilterChip label="Repeat customers" onRemove={() => { setBookingCountMin(""); setApplied(p => ({ ...p, bookingCountMin: "", page: 1 })); }} />}
            {applied.city      && <FilterChip label={`City: ${applied.city}`}   onRemove={() => { setCity(""); setApplied(p => ({ ...p, city: "", page: 1 })); }} />}
            {applied.state     && <FilterChip label={`State: ${applied.state}`} onRemove={() => { setState(""); setApplied(p => ({ ...p, state: "", page: 1 })); }} />}
            {applied.tenantId  && <FilterChip label="Tenant filter active"      onRemove={() => { setTenantId(""); setApplied(p => ({ ...p, tenantId: "", page: 1 })); }} />}
            {applied.hasComplaints === "yes" && <FilterChip label="Has Complaints" onRemove={() => { setHasComplaints(""); setApplied(p => ({ ...p, hasComplaints: "", page: 1 })); }} />}
            {applied.dateFrom  && <FilterChip label={`From: ${applied.dateFrom}`} onRemove={() => { setDateFrom(""); setApplied(p => ({ ...p, dateFrom: "", page: 1 })); }} />}
            {applied.dateTo    && <FilterChip label={`To: ${applied.dateTo}`}     onRemove={() => { setDateTo(""); setApplied(p => ({ ...p, dateTo: "", page: 1 })); }} />}
          </div>
        )}
      </Card>

      {/* Results table */}
      <Card padding={0}>
        <div style={{
          padding: "12px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize: 13, color: "var(--muted-text)" }}>
            {listFetch.loading
              ? "Loading…"
              : `${(meta?.total ?? 0).toLocaleString()} customer${(meta?.total ?? 0) !== 1 ? "s" : ""}${hasFilters ? " (filtered)" : ""}`}
          </span>
        </div>
        {listFetch.error ? (
          <div style={{ padding: "40px 20px", textAlign: "center" }}>
            <p style={{ fontSize: 14, color: "var(--danger-text,#b91c1c)", margin: "0 0 4px", fontWeight: 600 }}>
              Could not load customers.
            </p>
            <p style={{ fontSize: 13, color: "var(--muted-text)", margin: "0 0 4px" }}>{listFetch.error}</p>
            {listFetch.requestId && (
              <p style={{ fontSize: 11, color: "var(--muted-text)", margin: "0 0 14px", fontFamily: "monospace" }}>
                Request ID: {listFetch.requestId}
              </p>
            )}
            <Btn variant="secondary" size="sm" onClick={() => listFetch.refetch()}>Retry</Btn>
          </div>
        ) : (
          <DataTable
            columns={visibleColumns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={customers as unknown as Record<string, unknown>[]}
            loading={listFetch.loading}
            emptyText={
              hasFilters
                ? "No customers match the current filters. Try clearing some filters."
                : "No customers found yet. Customers will appear here after signup or first booking."
            }
          />
        )}
        {meta && <Pagination page={meta.page} pageSize={25} total={meta.total} pageCount={meta.total_pages} onPage={goToPage} />}
      </Card>

      <Modal open={!!actionModal} onClose={() => setActionModal(null)} title={
        actionModal?.type === "block" ? "Block Customer" : actionModal?.type === "unblock" ? "Unblock Customer"
        : actionModal?.type === "suspend" ? "Suspend Customer" : "Reactivate Customer"
      }>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Input label="Reason (required)" placeholder="Why is this action being taken?" value={actionReason} onChange={setActionReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setActionModal(null)}>Cancel</Btn>
            <Btn variant="danger" size="sm" disabled={!actionReason} onClick={confirmAction}>Confirm</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
