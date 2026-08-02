"use client";
import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import EnterpriseFilterBar, { FilterDef } from "./EnterpriseFilterBar";
import EnterprisePagination from "./EnterprisePagination";
import EnterpriseColumnManager, { ColumnDef } from "./EnterpriseColumnManager";

export interface GridColumn {
  key:      string;
  label:    string;
  visible?: boolean;
  order?:   number;
  width?:   number;
  render?:  (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

export interface RowAction {
  label:   string;
  onClick: (row: Record<string, unknown>) => void;
  danger?: boolean;
}

interface GridParams {
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
  enableColumnPrefs?: boolean;
  onExport?:          (params: GridParams) => void;
  emptyMessage?:      string;
  title?:             string;
  headerSlot?:        React.ReactNode;
}

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  open:        { background: "#fef9c3", color: "#854d0e" },
  pending:         { background: "#EDE9E3", color: "#6B5B4D" },
  active:      { background: "#dcfce7", color: "#166534" },
  approved:    { background: "#dcfce7", color: "#166534" },
  completed:   { background: "#bbf7d0", color: "#14532d" },
  resolved:    { background: "#d1fae5", color: "#065f46" },
  paid:        { background: "#d1fae5", color: "#065f46" },
  failed:      { background: "#fecaca", color: "#7f1d1d" },
  rejected:    { background: "#fee2e2", color: "#991b1b" },
  closed:      { background: "#f3f4f6", color: "#374151" },
  cancelled:   { background: "#f3f4f6", color: "#6b7280" },
  processing:  { background: "#f3e8ff", color: "#6b21a8" },
  escalated:   { background: "#ffedd5", color: "#9a3412" },
  refunded:        { background: "#CCFBF1", color: "#0F766E" },
  disputed:    { background: "#fef3c7", color: "#92400e" },
};

function StatusChip({ value }: { value: string }) {
  const style = STATUS_STYLE[value?.toLowerCase()] ?? { background: "#f3f4f6", color: "#374151" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 600,
      ...style,
    }}>
      {value?.replace(/_/g, " ")}
    </span>
  );
}

function RowActionsMenu({ actions, row }: { actions: RowAction[]; row: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  if (!actions.length) return null;
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button onClick={() => setOpen(o => !o)} style={{
        padding: "2px 6px", fontSize: 16, color: "var(--text-tertiary)",
        background: "none", border: "none", cursor: "pointer", lineHeight: 1, borderRadius: 6,
      }}>⋮</button>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 10 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", right: 0, top: "calc(100% + 2px)", zIndex: 20,
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, boxShadow: "var(--shadow-md)", padding: "4px 0", minWidth: 140,
          }}>
            {actions.map((a, i) => (
              <button key={i} onClick={() => { a.onClick(row); setOpen(false); }} style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "7px 14px", fontSize: 13, background: "none", border: "none",
                cursor: "pointer", fontFamily: "inherit",
                color: a.danger ? "var(--danger-text)" : "var(--text-primary)",
              }}>{a.label}</button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

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

function SortTh({ col, sortBy, sortDir, onClick }: {
  col: ColumnDef; sortBy: string; sortDir: string; onClick: () => void;
}) {
  const [hov, setHov] = useState(false);
  const active = sortBy === col.key;
  return (
    <th onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        width: col.width, padding: "10px 12px", textAlign: "left",
        fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
        background: hov ? "var(--surface-hover, var(--surface-sunken))" : "var(--surface-sunken)",
        cursor: "pointer", userSelect: "none", whiteSpace: "nowrap",
        transition: "background 0.1s",
      }}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        {col.label}
        {active && (
          <span style={{ color: "var(--brand)", fontSize: 10 }}>
            {sortDir === "asc" ? "↑" : "↓"}
          </span>
        )}
      </span>
    </th>
  );
}

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

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    setFilterValues(newFv); setPage(1);
    pushUrl(1, pageSize, sortBy, sortDir, search, newFv);
  };

  const handleSearchChange = (q: string) => {
    setSearch(q); setPage(1);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      pushUrl(1, pageSize, sortBy, sortDir, q, filterValues);
    }, 350);
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
    if (typeof value === "string" && (col.key === "status" || col.key === "priority")) {
      return <StatusChip value={value} />;
    }
    if (value === null || value === undefined) {
      return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
    }
    const str = String(value);
    if (str.length > 60) return <span title={str}>{str.slice(0, 58)}…</span>;
    return str;
  };

  const activeFilterCount = Object.values(data?.filters_applied ?? {}).filter(Boolean).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {(title || headerSlot) && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {title && (
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              {title}
            </h1>
          )}
          {headerSlot}
        </div>
      )}

      <EnterpriseFilterBar
        filters={filterDefs}
        values={filterValues}
        onChange={handleFilterChange}
        onReset={handleReset}
        onSearch={handleSearchChange}
        searchValue={search}
        rightSlot={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
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
              <button onClick={() => onExport?.(buildParams())} style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                height: 34, padding: "0 12px", fontSize: 12, borderRadius: 8,
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
              }}>
                <svg width="14" height="14" fill="none" viewBox="0 0 24 24"
                  stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export
              </button>
            )}
            <button onClick={load} title="Refresh" style={{
              height: 34, width: 34, display: "inline-flex", alignItems: "center",
              justifyContent: "center", fontSize: 16, borderRadius: 8,
              border: "1px solid var(--border)", background: "var(--surface)",
              color: "var(--text-secondary)", cursor: "pointer",
            }}>↺</button>
          </div>
        }
      />

      <div style={{
        border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden",
        background: "var(--surface)",
      }}>
        {loading && (
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: "64px 0", color: "var(--text-tertiary)", fontSize: 13, gap: 8,
          }}>
            <span style={{ fontSize: 18, animation: "spin 1s linear infinite",
              display: "inline-block" }}>⟳</span>
            Loading…
          </div>
        )}

        {error && !loading && (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", padding: "64px 0", gap: 8,
          }}>
            <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0 }}>
              Error: {error}
            </p>
            <button onClick={load} style={{
              fontSize: 12, color: "var(--brand)", background: "none",
              border: "none", cursor: "pointer", fontFamily: "inherit",
            }}>Retry</button>
          </div>
        )}

        {!loading && !error && data && (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {visibleColumns.map(c => (
                      <SortTh key={c.key} col={c} sortBy={sortBy} sortDir={sortDir}
                        onClick={() => handleSort(c.key)} />
                    ))}
                    {rowActions && (
                      <th style={{ width: 40, padding: "10px 12px",
                        background: "var(--surface-sunken)" }} />
                    )}
                  </tr>
                </thead>
                <tbody>
                  {(data.items?.length ?? 0) === 0 ? (
                    <tr>
                      <td colSpan={visibleColumns.length + (rowActions ? 1 : 0)}
                        style={{
                          padding: "48px 12px", textAlign: "center",
                          color: "var(--text-tertiary)", fontSize: 13,
                        }}>
                        {emptyMessage}
                      </td>
                    </tr>
                  ) : (data.items ?? []).map((row, i) => (
                    <tr key={String(row.id ?? i)}
                      onMouseEnter={() => setHoveredRow(i)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background: hoveredRow === i
                          ? "var(--surface-sunken)" : "var(--surface)",
                        transition: "background 0.1s",
                      }}>
                      {visibleColumns.map(c => (
                        <td key={c.key} style={{
                          padding: "10px 12px", color: "var(--text-primary)",
                          whiteSpace: "nowrap",
                        }}>
                          {renderCell(c, row)}
                        </td>
                      ))}
                      {rowActions && (
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>
                          <RowActionsMenu actions={rowActions(row)} row={row} />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
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

      {activeFilterCount > 0 && (
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
          {activeFilterCount} filter{activeFilterCount !== 1 ? "s" : ""} active
        </p>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
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
