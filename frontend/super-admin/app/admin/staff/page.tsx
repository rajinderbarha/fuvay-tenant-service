"use client";
import React, { useState, useCallback, useRef, useEffect } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, DataTable } from "../../../components/shared/ui";
import { adminStaffApi, AdminStaffMember, AdminStaffSummary, AdminStaffFilterOptions } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { Users, ChevronDown, X, Filter, Download } from "lucide-react";
import Link from "next/link";

const AVAIL_BADGE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  available: "success", busy: "warning", inactive: "muted",
};

function SummaryCard({ label, value, onClick, active }: {
  label: string; value: string | number; onClick?: () => void; active?: boolean;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: active ? "var(--primary)" : "var(--card-bg)",
        border: `1px solid ${active ? "var(--primary)" : "var(--border)"}`,
        borderRadius: 10, padding: "14px 18px", flex: 1, minWidth: 110,
        cursor: onClick ? "pointer" : "default",
        transition: "background 0.15s, border-color 0.15s",
      }}
    >
      <div style={{ fontSize: 11, color: active ? "rgba(255,255,255,.8)" : "var(--muted-text)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: active ? "#fff" : "var(--text)", fontVariantNumeric: "tabular-nums" }}>{value}</div>
    </div>
  );
}

function SearchDropdown({ label, options, value, onChange }: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);
  const filtered = options.filter(o => o.label.toLowerCase().includes(q.toLowerCase()));
  const selected = options.find(o => o.value === value);
  return (
    <div ref={ref} style={{ position: "relative", minWidth: 150 }}>
      <div
        onClick={() => setOpen(p => !p)}
        style={{
          display: "flex", alignItems: "center", gap: 6, height: 36, padding: "0 10px",
          border: `1px solid ${value ? "var(--primary)" : "var(--border)"}`,
          borderRadius:"var(--radius-md)", cursor: "pointer", fontSize: 13, color: value ? "var(--primary)" : "var(--muted-text)",
          background: "var(--card-bg)", userSelect: "none",
        }}
      >
        <span style={{ flex: 1 }}>{selected ? selected.label : label}</span>
        {value ? (
          <X size={13} onClick={e => { e.stopPropagation(); onChange(""); setQ(""); }} style={{ cursor: "pointer" }} />
        ) : (
          <ChevronDown size={13} />
        )}
      </div>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 100,
          background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
          boxShadow: "0 8px 24px rgba(0,0,0,.12)", minWidth: 200, maxHeight: 260, overflow: "auto",
        }}>
          <div style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)" }}>
            <input
              autoFocus
              placeholder="Search…"
              value={q}
              onChange={e => setQ(e.target.value)}
              style={{
                width: "100%", border: "none", outline: "none", fontSize: 13,
                background: "transparent", color: "var(--text)",
              }}
            />
          </div>
          {filtered.length === 0 ? (
            <div style={{ padding: "10px 12px", fontSize: 12, color: "var(--muted-text)" }}>No results</div>
          ) : filtered.map(o => (
            <div
              key={o.value}
              onClick={() => { onChange(o.value); setQ(""); setOpen(false); }}
              style={{
                padding: "8px 12px", fontSize: 13, cursor: "pointer",
                background: o.value === value ? "var(--primary-subtle, rgba(79,70,229,.08))" : "transparent",
                color: o.value === value ? "var(--primary)" : "var(--text)",
              }}
            >
              {o.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 5, height: 28, padding: "0 10px",
      background: "var(--primary-subtle, rgba(79,70,229,.1))", border: "1px solid var(--primary)",
      borderRadius: 20, fontSize: 12, color: "var(--primary)", fontWeight: 600,
    }}>
      {label}
      <X size={11} style={{ cursor: "pointer" }} onClick={onRemove} />
    </div>
  );
}

function StaffContent() {
  const [q, setQ] = useState("");
  const [inputQ, setInputQ] = useState("");
  const [availFilter, setAvailFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState<string>("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [page, setPage] = useState(1);

  const filters = useApi(useCallback(() => adminStaffApi.filterOptions(), []));
  const filterOpts: AdminStaffFilterOptions | null =
    (filters.data as { data?: AdminStaffFilterOptions } | null)?.data ?? null;

  const summaryFetch = useApi(useCallback(() => adminStaffApi.summary(), []));
  const summary: AdminStaffSummary | null =
    (summaryFetch.data as { data?: AdminStaffSummary } | null)?.data ?? null;

  const listFetch = useApi(
    useCallback(() => adminStaffApi.list({
      q: q || undefined,
      role: roleFilter || undefined,
      availability_status: availFilter || undefined,
      city: cityFilter || undefined,
      is_active: isActiveFilter === "" ? undefined : isActiveFilter === "true",
      page,
      page_size: 25,
    }), [q, roleFilter, availFilter, cityFilter, isActiveFilter, page]),
    [q, roleFilter, availFilter, cityFilter, isActiveFilter, page],
  );

  const listData = (listFetch.data as { data?: { staff: AdminStaffMember[]; meta: { page: number; total: number; total_pages: number } } } | null)?.data;
  const staffList = listData?.staff ?? [];
  const meta = listData?.meta;

  const activeFilterCount = [roleFilter, availFilter, cityFilter, isActiveFilter].filter(Boolean).length;

  const goToPage = (p: number) => { if (meta && p >= 1 && p <= meta.total_pages) setPage(p); };

  const AVAIL_OPTIONS = [
    { value: "available", label: "Available" },
    { value: "busy", label: "Busy" },
    { value: "inactive", label: "Inactive" },
  ];

  const ACTIVE_OPTIONS = [
    { value: "true", label: "Active" },
    { value: "false", label: "Deactivated" },
  ];

  const columns = [
    {
      key: "full_name", label: "Staff Member", width: 220,
      render: (_: unknown, row: AdminStaffMember) => (
        <Link href={`/admin/staff/${row.user_id}`} style={{ textDecoration: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", background: "var(--primary-subtle, rgba(79,70,229,.1))",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--primary)", fontWeight: 700, fontSize: 13, flexShrink: 0,
            }}>
              {(row.full_name || "?")[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)" }}>{row.full_name}</div>
              <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.email}</div>
            </div>
          </div>
        </Link>
      ),
    },
    {
      key: "phone", label: "Phone", width: 130,
      render: (_: unknown, row: AdminStaffMember) => (
        <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{row.phone || "—"}</span>
      ),
    },
    {
      key: "role", label: "Role", width: 120,
      render: (_: unknown, row: AdminStaffMember) => (
        <Badge variant="muted" size="sm">{row.role.replace(/_/g, " ")}</Badge>
      ),
    },
    {
      key: "tenant_name", label: "Provider",
      render: (_: unknown, row: AdminStaffMember) => (
        <div>
          <div style={{ fontSize: 13 }}>{row.tenant_name || "—"}</div>
          {row.tenant_city && <div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.tenant_city}</div>}
        </div>
      ),
    },
    {
      key: "availability_status", label: "Status", width: 120,
      render: (_: unknown, row: AdminStaffMember) => (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Badge variant={AVAIL_BADGE[row.availability_status] ?? "muted"} size="sm">
            {row.availability_status}
          </Badge>
          {!row.is_verified && (
            <Badge variant="warning" size="sm">Unverified</Badge>
          )}
        </div>
      ),
    },
    {
      key: "total_jobs", label: "Jobs", width: 110,
      render: (_: unknown, row: AdminStaffMember) => (
        <div style={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
          <span style={{ fontWeight: 600 }}>{row.total_jobs}</span>
          <span style={{ color: "var(--muted-text)", fontSize: 11 }}> ({row.completed_jobs} done)</span>
        </div>
      ),
    },
    {
      key: "average_rating", label: "Rating", width: 90,
      render: (_: unknown, row: AdminStaffMember) => (
        <span style={{ fontSize: 13 }}>
          {row.average_rating != null
            ? <><span style={{ color: "var(--warning)" }}>★</span> {row.average_rating.toFixed(1)}</>
            : <span style={{ color: "var(--muted-text)" }}>—</span>}
        </span>
      ),
    },
    {
      key: "last_job_at", label: "Last Active", width: 110,
      render: (_: unknown, row: AdminStaffMember) => {
        const d = row.last_job_at ? new Date(row.last_job_at) : null;
        return <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{d ? d.toLocaleDateString("en-IN") : "Never"}</span>;
      },
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Summary cards */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {summary ? (
          <>
            <SummaryCard label="Total Staff" value={summary.total} />
            <SummaryCard
              label="Available" value={summary.active - summary.busy}
              onClick={() => { setAvailFilter(availFilter === "available" ? "" : "available"); setPage(1); }}
              active={availFilter === "available"}
            />
            <SummaryCard
              label="Busy" value={summary.busy}
              onClick={() => { setAvailFilter(availFilter === "busy" ? "" : "busy"); setPage(1); }}
              active={availFilter === "busy"}
            />
            <SummaryCard
              label="Inactive" value={summary.inactive}
              onClick={() => { setAvailFilter(availFilter === "inactive" ? "" : "inactive"); setPage(1); }}
              active={availFilter === "inactive"}
            />
            <SummaryCard
              label="Unverified" value={summary.unverified}
              onClick={() => { setIsActiveFilter(""); setPage(1); }}
            />
            <SummaryCard label="New This Week" value={summary.new_this_week} />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ flex: 1, minWidth: 110, height: 72, background: "var(--border)", borderRadius: 10, opacity: 0.5 }} />
          ))
        )}
      </div>

      {/* Toolbar */}
      <Card padding={0}>
        <div style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <input
              placeholder="Search by name, email, or phone…"
              value={inputQ}
              onChange={e => setInputQ(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { setQ(inputQ); setPage(1); } }}
              style={{
                width: "100%", height: 36, padding: "0 12px", border: "1px solid var(--border)",
                borderRadius:"var(--radius-md)", fontSize: 13, background: "var(--card-bg)", color: "var(--text)",
                outline: "none", boxSizing: "border-box",
              }}
            />
          </div>

          <SearchDropdown
            label="Availability"
            options={AVAIL_OPTIONS}
            value={availFilter}
            onChange={v => { setAvailFilter(v); setPage(1); }}
          />

          <SearchDropdown
            label="Role"
            options={filterOpts?.roles ?? []}
            value={roleFilter}
            onChange={v => { setRoleFilter(v); setPage(1); }}
          />

          <Btn
            variant={showAdvanced ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setShowAdvanced(p => !p)}
          >
            <Filter size={13} style={{ marginRight: 4 }} />
            Filters {activeFilterCount > 0 && <span style={{ marginLeft: 4, background: "var(--primary)", color: "#fff", borderRadius: 10, padding: "0 6px", fontSize: 10 }}>{activeFilterCount}</span>}
          </Btn>

          <a
            href={adminStaffApi.export({
              ...(q ? { q } : {}),
              ...(roleFilter ? { role: roleFilter } : {}),
              ...(availFilter ? { availability_status: availFilter } : {}),
              ...(cityFilter ? { city: cityFilter } : {}),
            })}
            download="staff_export.csv"
          >
            <Btn variant="ghost" size="sm"><Download size={13} style={{ marginRight: 4 }} />CSV</Btn>
          </a>

          <Btn variant="ghost" size="sm" onClick={() => listFetch.refetch()}>↻</Btn>
        </div>

        {/* Advanced filters */}
        {showAdvanced && (
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", gap: 10, flexWrap: "wrap" }}>
            <SearchDropdown
              label="City"
              options={filterOpts?.cities ?? []}
              value={cityFilter}
              onChange={v => { setCityFilter(v); setPage(1); }}
            />
            <SearchDropdown
              label="Active Status"
              options={ACTIVE_OPTIONS}
              value={isActiveFilter}
              onChange={v => { setIsActiveFilter(v); setPage(1); }}
            />
          </div>
        )}

        {/* Active filter chips */}
        {activeFilterCount > 0 && (
          <div style={{ padding: "8px 16px", borderTop: "1px solid var(--border)", display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            {roleFilter && <FilterChip label={`Role: ${roleFilter}`} onRemove={() => { setRoleFilter(""); setPage(1); }} />}
            {availFilter && <FilterChip label={`Status: ${availFilter}`} onRemove={() => { setAvailFilter(""); setPage(1); }} />}
            {cityFilter && <FilterChip label={`City: ${cityFilter}`} onRemove={() => { setCityFilter(""); setPage(1); }} />}
            {isActiveFilter && <FilterChip label={isActiveFilter === "true" ? "Active only" : "Deactivated only"} onRemove={() => { setIsActiveFilter(""); setPage(1); }} />}
            <Btn variant="ghost" size="sm" onClick={() => {
              setRoleFilter(""); setAvailFilter(""); setCityFilter(""); setIsActiveFilter(""); setQ(""); setInputQ(""); setPage(1);
            }} style={{ fontSize: 11 }}>Clear all</Btn>
          </div>
        )}

        {/* Table */}
        <DataTable
          columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
          rows={staffList as unknown as Record<string, unknown>[]}
          loading={listFetch.loading}
          emptyText={activeFilterCount > 0 || q ? "No staff match the current filters." : "No staff members found on this platform."}
        />

        {/* Pagination */}
        {meta && meta.total_pages > 1 && (
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, color: "var(--muted-text)" }}>
              {meta.total} total · page {meta.page} of {meta.total_pages}
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => goToPage(page - 1)} disabled={page <= 1}>← Prev</Btn>
              <Btn variant="ghost" size="sm" onClick={() => goToPage(page + 1)} disabled={page >= meta.total_pages}>Next →</Btn>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function AdminStaffPage() {
  return (
    <AdminLayout activeNav="staff">
      <SectionHeader
        title="Staff Management"
        subtitle="View and manage staff across the entire platform"
        icon={<Users size={18} />}
      />
      <StaffContent />
    </AdminLayout>
  );
}
