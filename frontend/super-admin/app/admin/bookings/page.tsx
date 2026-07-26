"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, DataTable, SectionHeader } from "../../../components/shared/ui";
import {
  adminBookingsApi,
  AdminBooking, AdminBookingListParams, AdminBookingSummary, AdminBookingFilterOptions,
} from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import {
  Search, Filter, Download, RefreshCw, ExternalLink, X, ChevronDown,
  AlertTriangle, RotateCcw,
} from "lucide-react";
import Link from "next/link";

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  pending_confirmation: "warning",
  confirmed: "info",
  in_progress: "info",
  completed: "success",
  cancelled: "danger",
  void: "muted",
  draft: "muted",
};

const STATUS_OPTS = [
  { value: "", label: "All Statuses" },
  { value: "pending_confirmation", label: "Pending Confirmation" },
  { value: "confirmed", label: "Confirmed" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "void", label: "Void" },
  { value: "draft", label: "Draft" },
];

const SORT_OPTS = [
  { value: "created_at:desc", label: "Newest First" },
  { value: "created_at:asc",  label: "Oldest First" },
  { value: "scheduled_at:asc", label: "Scheduled Soon" },
  { value: "estimated_amount:desc", label: "Highest Amount" },
  { value: "estimated_amount:asc",  label: "Lowest Amount" },
];

// ── Small helpers ─────────────────────────────────────────────────────────────

function fmt(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function fmtAmt(n: number | null | undefined) {
  if (n == null) return "—";
  return `₹${n.toLocaleString("en-IN")}`;
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted-text)", textTransform: "uppercase",
      letterSpacing: "0.06em", marginBottom: 4 }}>
      {children}
    </div>
  );
}

// ── Async Tenant Selector ─────────────────────────────────────────────────────
interface AsyncTenantSelectProps {
  value: string;
  valueName: string;
  onChange: (id: string, name: string) => void;
}
function AsyncTenantSelect({ value, valueName, onChange }: AsyncTenantSelectProps) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: string; name: string; city: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    function h(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!open) return;
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await adminBookingsApi.tenantSearch(q);
        setResults((res as { data?: { tenants: { id: string; name: string; city: string }[] } })?.data?.tenants ?? []);
      } catch { setResults([]); } finally { setLoading(false); }
    }, 300);
  }, [q, open]);

  return (
    <div ref={ref} style={{ position: "relative", minWidth: 200 }}>
      <Label>Provider / Tenant</Label>
      <button type="button" onClick={() => setOpen(!open)} style={{
        width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "7px 10px", border: "1px solid var(--border)", borderRadius: 6,
        background: "var(--input-bg, var(--card-bg))", color: "var(--text)", fontSize: 13, cursor: "pointer", gap: 6,
      }}>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, textAlign: "left" }}>
          {value ? valueName || "Provider selected" : "All Providers"}
        </span>
        <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
          {value && <span onClick={e => { e.stopPropagation(); onChange("", ""); setQ(""); }} style={{ cursor: "pointer", color: "var(--muted-text)" }}><X size={11} /></span>}
          <ChevronDown size={13} style={{ color: "var(--muted-text)" }} />
        </div>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 300,
          background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,0.12)", overflow: "hidden",
        }}>
          <div style={{ padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>
            <input autoFocus value={q} onChange={e => setQ(e.target.value)}
              placeholder="Search provider name, city…"
              style={{ width: "100%", border: "none", outline: "none", fontSize: 13,
                background: "transparent", color: "var(--text)", padding: "2px 0" }} />
          </div>
          <div style={{ maxHeight: 220, overflowY: "auto" }}>
            <div onClick={() => { onChange("", ""); setOpen(false); }}
              style={{ padding: "7px 12px", fontSize: 13, cursor: "pointer", color: "var(--muted-text)" }}>
              All Providers
            </div>
            {loading ? (
              <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--muted-text)" }}>Searching…</div>
            ) : results.length === 0 ? (
              <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--muted-text)" }}>No providers found</div>
            ) : results.map(t => (
              <div key={t.id} onClick={() => { onChange(t.id, t.name); setOpen(false); setQ(""); }}
                style={{
                  padding: "7px 12px", fontSize: 13, cursor: "pointer",
                  background: value === t.id ? "var(--primary-bg, rgba(242,153,74,0.06))" : "transparent",
                  color: value === t.id ? "var(--primary)" : "var(--text)",
                }}>
                <div style={{ fontWeight: 500 }}>{t.name}</div>
                {t.city && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{t.city}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Summary Card ──────────────────────────────────────────────────────────────
function SummaryCard({
  label, value, color, onClick, active,
}: {
  label: string; value: number; color?: string; onClick?: () => void; active?: boolean;
}) {
  return (
    <div onClick={onClick} style={{
      background: active ? "var(--primary)" : "var(--card-bg)",
      border: `1px solid ${active ? "var(--primary)" : "var(--border)"}`,
      borderRadius:"var(--radius-md)", padding: "14px 18px", flex: 1, minWidth: 90,
      cursor: onClick ? "pointer" : "default",
      transition: "all 0.15s",
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: active ? "#fff" : (color ?? "var(--text)"), fontVariantNumeric: "tabular-nums" }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontSize: 11, color: active ? "rgba(255,255,255,0.8)" : "var(--muted-text)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ── Filter chip ───────────────────────────────────────────────────────────────
function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: "var(--primary-bg, rgba(242,153,74,0.08))",
      border: "1px solid var(--primary-border, rgba(242,153,74,0.25))",
      color: "var(--primary)", borderRadius: 999, padding: "2px 8px 2px 10px",
      fontSize: 12, fontWeight: 500,
    }}>
      {label}
      <span onClick={onRemove} style={{ cursor: "pointer", display: "flex", alignItems: "center" }}><X size={11} /></span>
    </span>
  );
}

// ── Native select helper ──────────────────────────────────────────────────────
function NativeSelect({ label, value, onChange, options }: {
  label: string; value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <select value={value} onChange={e => onChange(e.target.value)} style={{
        padding: "7px 10px", border: "1px solid var(--border)", borderRadius: 6,
        background: "var(--input-bg, var(--card-bg))", color: "var(--text)",
        fontSize: 13, width: "100%", cursor: "pointer", outline: "none",
      }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ── Text input helper ─────────────────────────────────────────────────────────
function TextInput({ label, value, onChange, placeholder, type = "text" }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string;
}) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          padding: "7px 10px", border: "1px solid var(--border)", borderRadius: 6,
          background: "var(--input-bg, var(--card-bg))", color: "var(--text)",
          fontSize: 13, width: "100%", outline: "none", boxSizing: "border-box",
        }} />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function AdminBookingsPage() {
  return (
    <AdminLayout activeNav="bookings">
      <SectionHeader title="Bookings" subtitle="Platform-wide bookings across all providers." />
      <BookingsContent />
    </AdminLayout>
  );
}

interface AppliedFilters extends AdminBookingListParams {
  page: number;
  tenantName: string;
}

const EMPTY_APPLIED: AppliedFilters = {
  q: "", tenant_id: "", tenantName: "", customer_id: "", status: "",
  category: "", service_id: "", city: "", state: "", district: "", zipcode: "",
  date_from: "", date_to: "", scheduled_from: "", scheduled_to: "",
  amount_min: undefined, amount_max: undefined,
  sort_by: "created_at", sort_dir: "desc", page: 1, page_size: 25,
};

function BookingsContent() {
  // Draft filter state (not yet applied)
  const [q,             setQ]             = useState("");
  const [statusFilter,  setStatusFilter]  = useState("");
  const [dateFrom,      setDateFrom]      = useState("");
  const [dateTo,        setDateTo]        = useState("");
  const [tenantId,      setTenantId]      = useState("");
  const [tenantName,    setTenantName]    = useState("");
  const [category,      setCategory]      = useState("");
  const [city,          setCity]          = useState("");
  const [state,         setState]         = useState("");
  const [district,      setDistrict]      = useState("");
  const [zipcode,       setZipcode]       = useState("");
  const [amtMin,        setAmtMin]        = useState("");
  const [amtMax,        setAmtMax]        = useState("");
  const [schedFrom,     setSchedFrom]     = useState("");
  const [schedTo,       setSchedTo]       = useState("");
  const [sortOpt,       setSortOpt]       = useState("created_at:desc");
  const [pageSize,      setPageSize]      = useState(25);
  const [showAdvanced,  setShowAdvanced]  = useState(false);

  // Applied state (triggers re-fetch)
  const [applied, setApplied] = useState<AppliedFilters>({ ...EMPTY_APPLIED });

  const filtersFetch  = useApi(useCallback(() => adminBookingsApi.filterOptions(), []));
  const summaryFetch  = useApi(useCallback(() => adminBookingsApi.summary(), []));

  const listFetch = useApi(useCallback(() => {
    const [sort_by, sort_dir] = (applied.sort_by + ":" + applied.sort_dir).split(":");
    return adminBookingsApi.list({
      q:              applied.q || undefined,
      tenant_id:      applied.tenant_id || undefined,
      status:         applied.status || undefined,
      category:       applied.category || undefined,
      city:           applied.city || undefined,
      state:          applied.state || undefined,
      district:       applied.district || undefined,
      zipcode:        applied.zipcode || undefined,
      date_from:      applied.date_from || undefined,
      date_to:        applied.date_to || undefined,
      scheduled_from: applied.scheduled_from || undefined,
      scheduled_to:   applied.scheduled_to || undefined,
      amount_min:     applied.amount_min,
      amount_max:     applied.amount_max,
      sort_by,
      sort_dir,
      page:           applied.page,
      page_size:      applied.page_size ?? 25,
    });
  }, [applied]));

  type ListData = { bookings: AdminBooking[]; meta: { page: number; total: number; total_pages: number } };
  const listData = (listFetch.data as { data?: ListData } | null)?.data;
  const bookings = listData?.bookings ?? [];
  const meta     = listData?.meta;
  const summary  = (summaryFetch.data as { data?: AdminBookingSummary } | null)?.data;
  const filterOpts = (filtersFetch.data as { data?: AdminBookingFilterOptions } | null)?.data;

  function buildSort() {
    const parts = sortOpt.split(":");
    return { sort_by: parts[0], sort_dir: parts[1] ?? "desc" };
  }

  function applyFilters() {
    const { sort_by, sort_dir } = buildSort();
    setApplied({
      q, tenant_id: tenantId, tenantName,
      status: statusFilter, category, city, state, district, zipcode,
      date_from: dateFrom, date_to: dateTo,
      scheduled_from: schedFrom, scheduled_to: schedTo,
      amount_min: amtMin ? parseFloat(amtMin) : undefined,
      amount_max: amtMax ? parseFloat(amtMax) : undefined,
      sort_by, sort_dir, page: 1, page_size: pageSize,
    });
  }

  function resetAll() {
    setQ(""); setStatusFilter(""); setDateFrom(""); setDateTo("");
    setTenantId(""); setTenantName(""); setCategory(""); setCity("");
    setState(""); setDistrict(""); setZipcode(""); setAmtMin(""); setAmtMax("");
    setSchedFrom(""); setSchedTo(""); setSortOpt("created_at:desc"); setPageSize(25);
    setApplied({ ...EMPTY_APPLIED });
    setShowAdvanced(false);
  }

  function goToPage(p: number) {
    setApplied(prev => ({ ...prev, page: p }));
  }

  function applyStatusCard(s: string) {
    setStatusFilter(s);
    setApplied(prev => ({ ...prev, status: s, page: 1 }));
  }

  function exportCsv() {
    const params: Record<string, string> = {};
    if (applied.q)              params.q             = applied.q;
    if (applied.status)         params.status        = applied.status;
    if (applied.tenant_id)      params.tenant_id     = applied.tenant_id;
    if (applied.category)       params.category      = applied.category;
    if (applied.city)           params.city          = applied.city;
    if (applied.state)          params.state         = applied.state;
    if (applied.date_from)      params.date_from     = applied.date_from;
    if (applied.date_to)        params.date_to       = applied.date_to;
    const path = adminBookingsApi.export(params);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = (typeof window !== "undefined" ? localStorage.getItem("serviceos_admin_token") : null) ?? "";
    fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `bookings-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
      })
      .catch(err => console.error("Export failed:", err));
  }

  // Compute active filter chips
  const activeChips: { key: string; label: string; clear: () => void }[] = [];
  if (applied.q)             activeChips.push({ key: "q",         label: `"${applied.q}"`,              clear: () => setApplied(p => ({ ...p, q: "",        page: 1 })) });
  if (applied.status)        activeChips.push({ key: "status",    label: applied.status.replace(/_/g, " "),    clear: () => setApplied(p => ({ ...p, status: "", page: 1 })) });
  if (applied.tenant_id)     activeChips.push({ key: "tenant",    label: `Provider: ${applied.tenantName}`,   clear: () => setApplied(p => ({ ...p, tenant_id: "", tenantName: "", page: 1 })) });
  if (applied.category)      activeChips.push({ key: "category",  label: `Cat: ${applied.category}`,          clear: () => setApplied(p => ({ ...p, category: "", page: 1 })) });
  if (applied.city)          activeChips.push({ key: "city",      label: `City: ${applied.city}`,             clear: () => setApplied(p => ({ ...p, city: "", page: 1 })) });
  if (applied.state)         activeChips.push({ key: "state",     label: `State: ${applied.state}`,           clear: () => setApplied(p => ({ ...p, state: "", page: 1 })) });
  if (applied.district)      activeChips.push({ key: "district",  label: `District: ${applied.district}`,     clear: () => setApplied(p => ({ ...p, district: "", page: 1 })) });
  if (applied.zipcode)       activeChips.push({ key: "zipcode",   label: `Pin: ${applied.zipcode}`,           clear: () => setApplied(p => ({ ...p, zipcode: "", page: 1 })) });
  if (applied.date_from)     activeChips.push({ key: "from",      label: `From: ${applied.date_from}`,        clear: () => setApplied(p => ({ ...p, date_from: "", page: 1 })) });
  if (applied.date_to)       activeChips.push({ key: "to",        label: `To: ${applied.date_to}`,            clear: () => setApplied(p => ({ ...p, date_to: "", page: 1 })) });
  if (applied.amount_min != null) activeChips.push({ key: "amtMin", label: `Min: ₹${applied.amount_min}`,    clear: () => setApplied(p => ({ ...p, amount_min: undefined, page: 1 })) });
  if (applied.amount_max != null) activeChips.push({ key: "amtMax", label: `Max: ₹${applied.amount_max}`,    clear: () => setApplied(p => ({ ...p, amount_max: undefined, page: 1 })) });
  const hasFilters = activeChips.length > 0;

  // Table columns
  const columns = [
    {
      key: "booking_number", label: "Booking #", width: 130,
      render: (_: unknown, row: AdminBooking) => (
        <Link href={`/admin/bookings/${row.id}`}
          style={{ color: "var(--primary)", fontWeight: 600, textDecoration: "none",
            fontFamily: "monospace", fontSize: 12 }}>
          {row.booking_number}
        </Link>
      ),
    },
    {
      key: "tenant_name", label: "Provider",
      render: (_: unknown, row: AdminBooking) => (
        <div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>{row.provider_name || row.tenant_name || "—"}</div>
          {row.city && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.city}</div>}
        </div>
      ),
    },
    {
      key: "customer_name", label: "Customer",
      render: (_: unknown, row: AdminBooking) => (
        <div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>{row.customer_name || "—"}</div>
          {row.customer_phone && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.customer_phone}</div>}
        </div>
      ),
    },
    {
      key: "category_name", label: "Service",
      render: (_: unknown, row: AdminBooking) => (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>{row.category_name || "—"}</div>
          {row.service_name && row.service_name !== row.category_name && (
            <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.service_name}</div>
          )}
        </div>
      ),
    },
    {
      key: "status", label: "Status", width: 150,
      render: (_: unknown, row: AdminBooking) => (
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Badge variant={STATUS_BADGE[row.status] ?? "muted"}>
            {row.status.replace(/_/g, " ")}
          </Badge>
          {row.sla_breached && (
            <span style={{ fontSize: 10, color: "var(--danger-text, #b91c1c)", display: "flex", alignItems: "center", gap: 2 }}>
              <AlertTriangle size={10} /> SLA breached
            </span>
          )}
        </div>
      ),
    },
    {
      key: "assignment_status", label: "Assignment", width: 100,
      render: (_: unknown, row: AdminBooking) => (
        <Badge variant={row.assignment_status === "assigned" ? "success" : "muted"}>
          {row.assignment_status}
        </Badge>
      ),
    },
    {
      key: "city", label: "Location", width: 120,
      render: (_: unknown, row: AdminBooking) => (
        <div style={{ fontSize: 12 }}>
          <div>{row.city || "—"}</div>
          {row.zipcode && <div style={{ color: "var(--muted-text)" }}>{row.zipcode}</div>}
        </div>
      ),
    },
    {
      key: "estimated_amount", label: "Amount", width: 90,
      render: (_: unknown, row: AdminBooking) => (
        <span style={{ fontFamily: "monospace", fontSize: 13 }}>{fmtAmt(row.estimated_amount)}</span>
      ),
    },
    {
      key: "scheduled_at", label: "Scheduled", width: 100,
      render: (_: unknown, row: AdminBooking) => (
        <span style={{ fontSize: 12, color: "var(--muted-text)" }}>
          {row.scheduled_at ? fmt(row.scheduled_at) : (row.preferred_date || "—")}
        </span>
      ),
    },
    {
      key: "created_at", label: "Created", width: 90,
      render: (_: unknown, row: AdminBooking) => (
        <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{fmt(row.created_at)}</span>
      ),
    },
    {
      key: "id", label: "", width: 36,
      render: (_: unknown, row: AdminBooking) => (
        <Link href={`/admin/bookings/${row.id}`} style={{ color: "var(--muted-text)", display: "flex" }}>
          <ExternalLink size={14} />
        </Link>
      ),
    },
  ];

  const advancedFilterCount = [
    tenantId, category, city, state, district, zipcode,
    amtMin, amtMax, schedFrom, schedTo,
  ].filter(Boolean).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Summary cards ─────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {summaryFetch.loading ? (
          [...Array(8)].map((_, i) => (
            <div key={i} style={{
              flex: 1, minWidth: 90, height: 62, borderRadius:"var(--radius-md)",
              background: "var(--skeleton-bg, rgba(0,0,0,0.05))", animation: "pulse 1.5s infinite",
            }} />
          ))
        ) : summary ? (
          <>
            <SummaryCard label="Total"     value={summary.total}   />
            <SummaryCard label="Today"     value={summary.today}   color="var(--primary)" />
            <SummaryCard label="Pending"   value={summary.pending_confirmation}
              color="var(--warning-text,#b45309)"
              active={applied.status === "pending_confirmation"}
              onClick={() => applyStatusCard("pending_confirmation")} />
            <SummaryCard label="Confirmed" value={summary.confirmed}
              color="var(--primary)"
              active={applied.status === "confirmed"}
              onClick={() => applyStatusCard("confirmed")} />
            <SummaryCard label="Scheduled" value={summary.scheduled} color="var(--primary)" />
            <SummaryCard label="Completed" value={summary.completed}
              color="var(--success-text,var(--success))"
              active={applied.status === "completed"}
              onClick={() => applyStatusCard("completed")} />
            <SummaryCard label="Cancelled" value={summary.cancelled}
              color="var(--danger-text,#b91c1c)"
              active={applied.status === "cancelled"}
              onClick={() => applyStatusCard("cancelled")} />
            <SummaryCard label="Unassigned" value={summary.unassigned} color="var(--warning-text,#b45309)" />
            {summary.at_risk > 0 && (
              <SummaryCard label="At Risk / SLA" value={summary.at_risk} color="var(--danger-text,#b91c1c)" />
            )}
          </>
        ) : null}
      </div>

      {/* ── Toolbar ───────────────────────────────────────────────────────── */}
      <Card padding={14}>
        {/* Main row */}
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 2, minWidth: 220 }}>
            <Label>Search</Label>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{
                position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)",
                color: "var(--muted-text)", pointerEvents: "none",
              }} />
              <input value={q} onChange={e => setQ(e.target.value)}
                onKeyDown={e => e.key === "Enter" && applyFilters()}
                placeholder="Booking #, customer, provider, city…"
                style={{
                  width: "100%", padding: "7px 10px 7px 30px",
                  border: "1px solid var(--border)", borderRadius: 6,
                  background: "var(--input-bg, var(--card-bg))", color: "var(--text)",
                  fontSize: 13, outline: "none", boxSizing: "border-box",
                }} />
            </div>
          </div>
          <div style={{ minWidth: 170 }}>
            <NativeSelect label="Status" value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTS} />
          </div>
          <div style={{ minWidth: 110 }}>
            <TextInput label="From" type="date" value={dateFrom} onChange={setDateFrom} />
          </div>
          <div style={{ minWidth: 110 }}>
            <TextInput label="To" type="date" value={dateTo} onChange={setDateTo} />
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "flex-end" }}>
            <Btn variant="secondary" size="sm" onClick={() => setShowAdvanced(!showAdvanced)}>
              <Filter size={14} style={{ marginRight: 4 }} />Filters
              {advancedFilterCount > 0 && (
                <span style={{
                  marginLeft: 5, background: "var(--primary)", color: "#fff",
                  borderRadius: 999, fontSize: 10, fontWeight: 700, padding: "1px 5px",
                }}>
                  {advancedFilterCount}
                </span>
              )}
            </Btn>
            <Btn variant="primary" size="sm" onClick={applyFilters}>
              <Search size={14} style={{ marginRight: 4 }} />Search
            </Btn>
            {hasFilters && (
              <Btn variant="ghost" size="sm" onClick={resetAll}>
                <RotateCcw size={13} style={{ marginRight: 3 }} />Reset
              </Btn>
            )}
            <Btn variant="ghost" size="sm" onClick={() => { listFetch.refetch(); summaryFetch.refetch(); }}>
              <RefreshCw size={14} />
            </Btn>
            <Btn variant="ghost" size="sm" onClick={exportCsv}>
              <Download size={14} style={{ marginRight: 4 }} />CSV
            </Btn>
          </div>
        </div>

        {/* Advanced drawer */}
        {showAdvanced && (
          <div style={{
            marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)",
            display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10,
          }}>
            <AsyncTenantSelect value={tenantId} valueName={tenantName}
              onChange={(id, name) => { setTenantId(id); setTenantName(name); }} />
            <div>
              <NativeSelect label="Category" value={category} onChange={setCategory}
                options={[
                  { value: "", label: "All Categories" },
                  ...(filterOpts?.categories ?? []),
                ]} />
            </div>
            <TextInput label="City" value={city} onChange={setCity} placeholder="e.g. Jalandhar" />
            <TextInput label="State" value={state} onChange={setState} placeholder="e.g. Punjab" />
            <TextInput label="District" value={district} onChange={setDistrict} placeholder="District" />
            <TextInput label="Pincode / Zip" value={zipcode} onChange={setZipcode} placeholder="e.g. 144001" />
            <TextInput label="Amount Min (₹)" type="number" value={amtMin} onChange={setAmtMin} placeholder="0" />
            <TextInput label="Amount Max (₹)" type="number" value={amtMax} onChange={setAmtMax} placeholder="99999" />
            <TextInput label="Scheduled From" type="date" value={schedFrom} onChange={setSchedFrom} />
            <TextInput label="Scheduled To" type="date" value={schedTo} onChange={setSchedTo} />
            <div>
              <NativeSelect label="Sort" value={sortOpt} onChange={setSortOpt} options={SORT_OPTS} />
            </div>
            <div>
              <NativeSelect label="Per page" value={String(pageSize)} onChange={v => setPageSize(Number(v))}
                options={[
                  { value: "25", label: "25 / page" },
                  { value: "50", label: "50 / page" },
                  { value: "100", label: "100 / page" },
                ]} />
            </div>
          </div>
        )}

        {/* Active filter chips */}
        {activeChips.length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
            {activeChips.map(chip => (
              <Chip key={chip.key} label={chip.label} onRemove={chip.clear} />
            ))}
            <button onClick={resetAll} style={{
              fontSize: 11, color: "var(--muted-text)", background: "none", border: "none",
              cursor: "pointer", textDecoration: "underline",
            }}>
              Clear all
            </button>
          </div>
        )}
      </Card>

      {/* ── Results table ─────────────────────────────────────────────────── */}
      <Card padding={0}>
        {/* Table header */}
        <div style={{
          padding: "12px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8,
        }}>
          <span style={{ fontSize: 13, color: "var(--muted-text)" }}>
            {listFetch.loading
              ? "Loading…"
              : listFetch.error
              ? ""
              : `${(meta?.total ?? 0).toLocaleString()} booking${(meta?.total ?? 0) !== 1 ? "s" : ""}${hasFilters ? " (filtered)" : " platform-wide"}`}
          </span>
          {meta && meta.total_pages > 1 && (
            <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <Btn variant="ghost" size="sm" disabled={meta.page <= 1} onClick={() => goToPage(meta.page - 1)}>‹ Prev</Btn>
              <span style={{ fontSize: 12, color: "var(--muted-text)", padding: "0 4px" }}>
                Page {meta.page} of {meta.total_pages}
              </span>
              <Btn variant="ghost" size="sm" disabled={meta.page >= meta.total_pages} onClick={() => goToPage(meta.page + 1)}>Next ›</Btn>
            </div>
          )}
        </div>

        {/* Error state */}
        {listFetch.error && !listFetch.loading ? (
          <div style={{ padding: 40, textAlign: "center" }}>
            <AlertTriangle size={32} style={{ color: "var(--danger-text, #b91c1c)", marginBottom: 12 }} />
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--danger-text, #b91c1c)", margin: "0 0 4px" }}>
              Could not load bookings
            </p>
            <p style={{ fontSize: 12, color: "var(--muted-text)", margin: "0 0 16px" }}>
              {String(listFetch.error)}
            </p>
            <Btn variant="secondary" size="sm" onClick={() => listFetch.refetch()}>
              <RotateCcw size={13} style={{ marginRight: 4 }} /> Retry
            </Btn>
          </div>
        ) : (
          <DataTable
            columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={bookings as unknown as Record<string, unknown>[]}
            loading={listFetch.loading}
            emptyText={
              hasFilters
                ? "No bookings match the current filters. Try clearing some filters or broadening your search."
                : "No bookings on the platform yet. Bookings will appear here once customers start placing orders."
            }
          />
        )}

        {/* Bottom pagination */}
        {meta && meta.total_pages > 1 && !listFetch.error && (
          <div style={{
            padding: "10px 16px", borderTop: "1px solid var(--border)",
            display: "flex", justifyContent: "flex-end", gap: 4,
          }}>
            <Btn variant="ghost" size="sm" disabled={meta.page <= 1} onClick={() => goToPage(1)}>«</Btn>
            <Btn variant="ghost" size="sm" disabled={meta.page <= 1} onClick={() => goToPage(meta.page - 1)}>‹</Btn>
            <span style={{ padding: "4px 10px", fontSize: 12, color: "var(--muted-text)" }}>
              {meta.page} / {meta.total_pages}
            </span>
            <Btn variant="ghost" size="sm" disabled={meta.page >= meta.total_pages} onClick={() => goToPage(meta.page + 1)}>›</Btn>
            <Btn variant="ghost" size="sm" disabled={meta.page >= meta.total_pages} onClick={() => goToPage(meta.total_pages)}>»</Btn>
          </div>
        )}
      </Card>
    </div>
  );
}
