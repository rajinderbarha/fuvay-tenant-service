"use client";
import { TableSurface } from "@serviceos/design-system";
import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import ReactDOM from "react-dom";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import EnterpriseFilterBar, { FilterDef } from "./EnterpriseFilterBar";
import EnterprisePagination from "./EnterprisePagination";
import EnterpriseColumnManager, { ColumnDef } from "./EnterpriseColumnManager";
import { PageHeader } from "@serviceos/design-system";
import { Btn } from "../shared/ui";

export interface GridColumn {
  key:      string;
  label:    string;
  visible?: boolean;
  order?:   number;
  width?:   number;
  chip?:    boolean;
  render?:  (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

export interface RowAction {
  label:     string;
  onClick:   (row: Record<string, unknown>) => void;
  danger?:   boolean;
  divider?:  boolean;
}

export interface GridParams {
  page:           number;
  page_size:      number;
  sort_by:        string;
  sort_direction: string;
  search?:        string;
  [key: string]:  unknown;
}

export interface GridData {
  items:      Record<string, unknown>[];
  pagination: {
    page: number; page_size: number;
    total_items: number; total_pages: number;
    has_next: boolean; has_previous: boolean;
  };
  sort: { sort_by: string; sort_direction: string };
  filters_applied: Record<string, unknown>;
  available_columns?: ColumnDef[];
}

interface Props {
  resourceKey:        string;
  fetchFn:            (params: GridParams) => Promise<GridData>;
  columns:            GridColumn[];
  filters?:           FilterDef[];
  defaultSort?:       { sort_by: string; sort_direction: "asc" | "desc" };
  rowActions?:        (row: Record<string, unknown>) => RowAction[];
  enableExport?:      boolean;
  enableSavedViews?:  boolean;
  enableColumnPrefs?: boolean;
  onExport?:          (params: GridParams) => void;
  emptyMessage?:      string;
  title?:             string;
  description?:       string;
  headerSlot?:        React.ReactNode;
}

// ── Status chips ──────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  open:            { background: "#fef9c3", color: "#854d0e" },
  pending:         { background: "#EDE9E3", color: "#6B5B4D" },
  active:          { background: "#dcfce7", color: "#166534" },
  approved:        { background: "#dcfce7", color: "#166534" },
  verified:        { background: "#dcfce7", color: "#166534" },
  completed:       { background: "#bbf7d0", color: "#14532d" },
  resolved:        { background: "#d1fae5", color: "#065f46" },
  paid:            { background: "#d1fae5", color: "#065f46" },
  failed:          { background: "#fecaca", color: "#7f1d1d" },
  rejected:        { background: "#fee2e2", color: "#991b1b" },
  closed:          { background: "#f3f4f6", color: "#374151" },
  cancelled:       { background: "#f3f4f6", color: "#6b7280" },
  inactive:        { background: "#f3f4f6", color: "#6b7280" },
  suspended:       { background: "#ffedd5", color: "#9a3412" },
  processing:      { background: "#f3e8ff", color: "#6b21a8" },
  escalated:       { background: "#ffedd5", color: "#9a3412" },
  refunded:        { background: "#CCFBF1", color: "#0F766E" },
  disputed:        { background: "#fef3c7", color: "#92400e" },
  not_started:     { background: "#f3f4f6", color: "#6b7280" },
  under_review:    { background: "#fef3c7", color: "#92400e" },
  archived:        { background: "#f3f4f6", color: "#9ca3af" },
};

export function StatusChip({ value }: { value: string }) {
  const style = STATUS_STYLE[value?.toLowerCase()] ?? { background: "#f3f4f6", color: "#374151" };
  const label = value?.replace(/_/g, " ") ?? "";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 9px", borderRadius: 999, fontSize: 11, fontWeight: 600,
      whiteSpace: "nowrap", ...style,
    }}>
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

// ── Portal Row Actions menu ────────────────────────────────────────────────────

function RowActionsMenu({ actions, row }: { actions: RowAction[]; row: Record<string, unknown> }) {
  const [open,    setOpen]    = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0, above: false });
  const btnRef = useRef<HTMLButtonElement>(null);

  const handleToggle = useCallback(() => {
    if (!open && btnRef.current) {
      const rect    = btnRef.current.getBoundingClientRect();
      const menuH   = actions.filter(Boolean).length * 38 + 12;
      const menuW   = 192;
      const above   = window.innerHeight - rect.bottom < menuH + 12;
      const top     = above ? rect.top - menuH - 4 : rect.bottom + 4;
      const left    = Math.max(8, Math.min(rect.right - menuW, window.innerWidth - menuW - 8));
      setMenuPos({ top, left, above });
    }
    setOpen(o => !o);
  }, [open, actions]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!actions.length) return null;

  const portal = open && typeof document !== "undefined"
    ? ReactDOM.createPortal(
        <>
          {/* click-away backdrop */}
          <div
            style={{ position: "fixed", inset: 0, zIndex: 9998 }}
            onClick={() => setOpen(false)}
          />
          {/* menu */}
          <div style={{
            position: "fixed",
            top: menuPos.top, left: menuPos.left,
            zIndex: 9999, minWidth: 192,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            boxShadow: "0 8px 28px rgba(0,0,0,0.13), 0 2px 8px rgba(0,0,0,0.07)",
            padding: "4px 0", overflow: "hidden",
          }}>
            {actions.map((a, i) => {
              if (a.divider) {
                return <div key={`d${i}`} style={{ height: 1, background: "var(--border)", margin: "4px 0" }} />;
              }
              return (
                <button
                  type="button"
                  key={i}
                  onClick={() => { a.onClick(row); setOpen(false); }}
                  style={{
                    display: "block", width: "100%", textAlign: "left",
                    padding: "9px 16px", fontSize: 13, lineHeight: 1.3,
                    background: "none", border: "none", cursor: "pointer",
                    fontFamily: "inherit",
                    color: a.danger ? "var(--danger-text, var(--danger))" : "var(--text-primary)",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "none")}
                >
                  {a.label}
                </button>
              );
            })}
          </div>
        </>,
        document.body
      )
    : null;

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        ref={btnRef}
        onClick={handleToggle}
        aria-label="Row actions"
        style={{
          width: 30, height: 30,
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          fontSize: 18, color: "var(--text-tertiary)",
          background: open ? "var(--surface-sunken)" : "none",
          border: "none", cursor: "pointer", borderRadius: 6,
          transition: "background 0.1s, color 0.1s",
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = "var(--surface-sunken)";
          e.currentTarget.style.color      = "var(--text-primary)";
        }}
        onMouseLeave={e => {
          if (!open) {
            e.currentTarget.style.background = "none";
            e.currentTarget.style.color      = "var(--text-tertiary)";
          }
        }}
      >⋮</button>
      {portal}
    </div>
  );
}

// ── URL helpers ───────────────────────────────────────────────────────────────

const KNOWN_FILTER_PARAMS = new Set([
  "status", "category_id", "tenant_id", "offering_id", "customer_id",
  "staff_member_id", "date_from", "date_to", "created_from", "created_to",
  "updated_from", "updated_to", "record_type", "type", "priority",
  "payment_status", "commission_status", "assignment_status",
  "review_status", "complaint_status",
]);

function parseUrlState(
  sp: URLSearchParams,
  defaultSort: { sort_by: string; sort_direction: string },
  filterDefs: FilterDef[],
) {
  const page      = Math.max(1, parseInt(sp.get("page") ?? "1", 10) || 1);
  const page_size = Math.min(100, Math.max(10, parseInt(sp.get("page_size") ?? "25", 10) || 25));
  const sort_by   = sp.get("sort_by") || defaultSort.sort_by;
  const sort_dir  = ((sp.get("sort_direction") as "asc" | "desc") || defaultSort.sort_direction) as "asc" | "desc";
  const search    = sp.get("search") || "";

  const filterKeys = new Set([...filterDefs.map(f => f.key), ...KNOWN_FILTER_PARAMS]);
  const filterValues: Record<string, string> = {};
  filterKeys.forEach(k => { const v = sp.get(k); if (v) filterValues[k] = v; });

  return { page, page_size, sort_by, sort_dir, search, filterValues };
}

function buildUrlParams(
  page: number, pageSize: number,
  sortBy: string, sortDir: string,
  search: string, filterValues: Record<string, string>,
): URLSearchParams {
  const sp = new URLSearchParams();
  if (page > 1)        sp.set("page", String(page));
  if (pageSize !== 25) sp.set("page_size", String(pageSize));
  sp.set("sort_by", sortBy);
  sp.set("sort_direction", sortDir);
  if (search) sp.set("search", search);
  Object.entries(filterValues).forEach(([k, v]) => { if (v) sp.set(k, v); });
  return sp;
}

// ── Sort header ───────────────────────────────────────────────────────────────

function SortTh({ col, sortBy, sortDir, onClick }: {
  col: ColumnDef; sortBy: string; sortDir: string; onClick: () => void;
}) {
  const [hov, setHov] = useState(false);
  const active = sortBy === col.key;
  return (
    <th
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: col.width, padding: "11px 14px", textAlign: "left",
        fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
        textTransform: "uppercase", letterSpacing: "0.06em",
        background: hov ? "var(--surface-hover, var(--surface-sunken))" : "var(--surface-sunken)",
        cursor: "pointer", userSelect: "none", whiteSpace: "nowrap",
        borderBottom: "1px solid var(--border)",
        transition: "background 0.1s",
      }}
    >
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        {col.label}
        {active && (
          <span style={{ color: "var(--brand, #0f6b60)", fontSize: 10 }}>
            {sortDir === "asc" ? "↑" : "↓"}
          </span>
        )}
      </span>
    </th>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {[0, 1, 2, 3, 4].map(i => (
        <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} style={{ padding: "14px 14px" }}>
              <div style={{
                height: 14, borderRadius: 6,
                background: "var(--surface-sunken)",
                width: j === 0 ? "70%" : j === cols - 1 ? "40%" : "55%",
                animation: "shimmer 1.5s infinite",
              }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

function EnterpriseDataGridInner({
  resourceKey,
  fetchFn,
  columns: initialColumns,
  filters: filterDefs = [],
  defaultSort = { sort_by: "created_at", sort_direction: "desc" },
  rowActions,
  enableExport,
  enableColumnPrefs,
  onExport,
  emptyMessage = "No records found.",
  title,
  description,
  headerSlot,
}: Props) {
  const router       = useRouter();
  const pathname     = usePathname();
  const searchParams = useSearchParams();

  const initial = parseUrlState(searchParams, defaultSort, filterDefs);

  const [data,         setData]         = useState<GridData | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState<string | null>(null);
  const [page,         setPage]         = useState(initial.page);
  const [pageSize,     setPageSize]     = useState(initial.page_size);
  const [sortBy,       setSortBy]       = useState(initial.sort_by);
  const [sortDir,      setSortDir]      = useState<"asc" | "desc">(initial.sort_dir);
  const [search,       setSearch]       = useState(initial.search);
  const [filterValues, setFilterValues] = useState<Record<string, string>>(initial.filterValues);
  const [hoveredRow,   setHoveredRow]   = useState<number | null>(null);
  const [columns,      setColumns]      = useState<ColumnDef[]>(
    initialColumns.map((c, i) => ({
      key: c.key, label: c.label,
      visible: c.visible !== false, order: c.order ?? i, width: c.width,
    }))
  );

  const pushUrl = useCallback((
    p: number, ps: number, sb: string, sd: string,
    q: string, fv: Record<string, string>,
  ) => {
    const sp = buildUrlParams(p, ps, sb, sd, q, fv);
    const qs = sp.toString();
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [router, pathname]);

  const buildParams = useCallback((): GridParams => {
    const p: GridParams = { page, page_size: pageSize, sort_by: sortBy, sort_direction: sortDir };
    if (search) p.search = search;
    Object.entries(filterValues).forEach(([k, v]) => { if (v) p[k] = v; });
    return p;
  }, [page, pageSize, sortBy, sortDir, search, filterValues]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const result = await fetchFn(buildParams());
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }, [fetchFn, buildParams]);

  useEffect(() => { load(); }, [load]);

  const handleSort = (key: string) => {
    const newDir = sortBy === key ? (sortDir === "asc" ? "desc" : "asc") : "desc";
    setSortBy(key); setSortDir(newDir); setPage(1);
    pushUrl(1, pageSize, key, newDir, search, filterValues);
  };

  const handleFilterChange = (key: string, value: string) => {
    const newFv = { ...filterValues, [key]: value };
    if (!value) delete newFv[key];
    setFilterValues(newFv); setPage(1);
    pushUrl(1, pageSize, sortBy, sortDir, search, newFv);
  };

  const handleBatchFilterChange = useCallback((changes: Record<string, string>) => {
    const newFv = { ...filterValues, ...changes };
    Object.keys(newFv).forEach(k => { if (!newFv[k]) delete newFv[k]; });
    setFilterValues(newFv); setPage(1);
    pushUrl(1, pageSize, sortBy, sortDir, search, newFv);
  }, [filterValues, pageSize, sortBy, sortDir, search, pushUrl]);

  const handleSearchChange = (q: string) => {
    setSearch(q); setPage(1);
    pushUrl(1, pageSize, sortBy, sortDir, q, filterValues);
  };

  const handlePageChange = (p: number) => {
    setPage(p);
    pushUrl(p, pageSize, sortBy, sortDir, search, filterValues);
  };

  const handlePageSizeChange = (ps: number) => {
    setPageSize(ps); setPage(1);
    pushUrl(1, ps, sortBy, sortDir, search, filterValues);
  };

  const handleReset = () => {
    setFilterValues({}); setSearch("");
    setSortBy(defaultSort.sort_by); setSortDir(defaultSort.sort_direction); setPage(1);
    router.replace(pathname, { scroll: false });
  };

  const visibleColumns = columns.filter(c => c.visible).sort((a, b) => a.order - b.order);

  const renderCell = (col: ColumnDef, row: Record<string, unknown>) => {
    const value   = row[col.key];
    const gridCol = initialColumns.find(c => c.key === col.key);
    if (gridCol?.render) return gridCol.render(value, row);
    if (gridCol?.chip || col.key === "status" || col.key === "priority" || col.key === "verification_status") {
      if (typeof value === "string" && value) return <StatusChip value={value} />;
    }
    if (value === null || value === undefined || value === "") {
      return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
    }
    const str = String(value);
    if (str.length > 60) return <span title={str}>{str.slice(0, 58)}…</span>;
    return str;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Page header (outside card) */}
      {(title || headerSlot) && <div style={{ marginBottom: "var(--layout-page-gap)" }}>
        <PageHeader eyebrow="Platform operations" title={title ?? "Data workspace"} description={description} actions={headerSlot} />
      </div>}

      {/* Card: toolbar + table + pagination */}
      <div style={{
        border: "1px solid var(--border)", borderRadius: 12,
        background: "var(--surface)", overflow: "hidden",
      }}>
        {/* Toolbar inside card */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <EnterpriseFilterBar
            filters={filterDefs}
            values={filterValues}
            onChange={handleFilterChange}
            onBatchChange={handleBatchFilterChange}
            onReset={handleReset}
            onSearch={handleSearchChange}
            searchValue={search}
            rightSlot={
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {enableColumnPrefs && (
                  <EnterpriseColumnManager
                    columns={columns}
                    onChange={setColumns}
                    onReset={() => setColumns(initialColumns.map((c, i) => ({
                      key: c.key, label: c.label,
                      visible: c.visible !== false, order: c.order ?? i, width: c.width,
                    })))}
                  />
                )}
                {enableExport && (
                  <Btn
                    size="sm"
                    variant="secondary"
                    onClick={() => onExport?.(buildParams())}
                    title="Export"
                  >
                    <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export
                  </Btn>
                )}
                <button
                  type="button"
                  onClick={load}
                  title="Refresh"
                  style={{
                    height: 34, width: 34, display: "inline-flex", alignItems: "center",
                    justifyContent: "center", fontSize: 16, borderRadius: 8,
                    border: "1px solid var(--border)", background: "var(--surface)",
                    color: "var(--text-secondary)", cursor: "pointer",
                  }}
                >↺</button>
              </div>
            }
          />
        </div>

        {/* Summary row (total + loading state) */}
        {data && !loading && (
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "8px 16px",
            borderBottom: "1px solid var(--border)",
            background: "var(--surface-sunken)",
          }}>
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {data.pagination
                ? `${data.pagination.total_items.toLocaleString()} result${data.pagination.total_items !== 1 ? "s" : ""}`
                : ""}
            </span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{ overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {visibleColumns.map(c => (
                    <th key={c.key} style={{
                      padding: "11px 14px", textAlign: "left",
                      fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                      textTransform: "uppercase", letterSpacing: "0.06em",
                      background: "var(--surface-sunken)",
                      whiteSpace: "nowrap",
                    }}>{c.label}</th>
                  ))}
                  {rowActions && <th style={{ width: 48, background: "var(--surface-sunken)" }} />}
                </tr>
              </thead>
              <tbody>
                <SkeletonRows cols={visibleColumns.length + (rowActions ? 1 : 0)} />
              </tbody>
            </TableSurface>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", padding: "56px 24px", gap: 10,
          }}>
            <div style={{ fontSize: 28 }}>⚠</div>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--danger-text, var(--danger))", margin: 0 }}>
              Could not load data
            </p>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{error}</p>
            <button
              type="button"
              onClick={load}
              style={{
                marginTop: 4, fontSize: 13, color: "var(--brand, #0f6b60)",
                background: "none", border: "none", cursor: "pointer", fontFamily: "inherit",
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Table */}
        {!loading && !error && data && (
          <>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {visibleColumns.map(c => (
                      <SortTh key={c.key} col={c} sortBy={sortBy} sortDir={sortDir}
                        onClick={() => handleSort(c.key)} />
                    ))}
                    {rowActions && (
                      <th style={{
                        width: 48, padding: "11px 14px",
                        background: "var(--surface-sunken)",
                        borderBottom: "1px solid var(--border)",
                      }} />
                    )}
                  </tr>
                </thead>
                <tbody>
                  {(data.items?.length ?? 0) === 0 ? (
                    <tr>
                      <td
                        colSpan={visibleColumns.length + (rowActions ? 1 : 0)}
                        style={{
                          padding: "56px 24px", textAlign: "center",
                          color: "var(--text-tertiary)", fontSize: 13,
                        }}
                      >
                        <div style={{ fontSize: 28, marginBottom: 8 }}>○</div>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{emptyMessage}</div>
                        <div style={{ fontSize: 12 }}>
                          {Object.values(filterValues).some(Boolean)
                            ? "Try adjusting or clearing your filters."
                            : ""}
                        </div>
                      </td>
                    </tr>
                  ) : (data.items ?? []).map((row, i) => (
                    <tr
                      key={String(row.id ?? i)}
                      onMouseEnter={() => setHoveredRow(i)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background: hoveredRow === i ? "var(--surface-sunken)" : "var(--surface)",
                        transition: "background 0.1s",
                      }}
                    >
                      {visibleColumns.map(c => (
                        <td key={c.key} style={{
                          padding: "12px 14px", color: "var(--text-primary)",
                          verticalAlign: "middle",
                        }}>
                          {renderCell(c, row)}
                        </td>
                      ))}
                      {rowActions && (
                        <td style={{ padding: "12px 14px", textAlign: "right" }}>
                          <RowActionsMenu actions={rowActions(row)} row={row} />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>

            {data.pagination && (
              <EnterprisePagination
                pagination={data.pagination}
                onPage={handlePageChange}
                onPageSize={handlePageSizeChange}
              />
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes shimmer {
          0%   { opacity: 1; }
          50%  { opacity: 0.4; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export default function EnterpriseDataGrid(props: Props) {
  return (
    <Suspense fallback={<div style={{ padding: 24, color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>}>
      <EnterpriseDataGridInner {...props} />
    </Suspense>
  );
}
