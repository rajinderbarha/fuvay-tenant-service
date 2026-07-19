"use client";

import React, { useMemo, useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { Skeleton } from "./Skeleton";
import { EmptyState, ErrorState } from "./StateViews";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
  accessor?: (row: T) => string | number;
  align?: "left" | "right" | "center";
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  /** Renders a mobile card layout below this viewport width via CSS, falling
   * back to the table on wider screens. Both are in the DOM; CSS toggles
   * visibility to avoid a JS resize listener. */
  mobileCard?: (row: T) => React.ReactNode;
}

export function DataTable<T>({ columns, rows, rowKey, loading, error, emptyTitle = "No records found", emptyDescription, mobileCard }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.accessor) return rows;
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = col.accessor!(a);
      const bv = col.accessor!(b);
      if (av === bv) return 0;
      return av > bv ? 1 : -1;
    });
    if (sortDir === "desc") copy.reverse();
    return copy;
  }, [rows, sortKey, sortDir, columns]);

  if (error) return <ErrorState title="Couldn't load data" description={error} />;

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} height="2.5rem" />
        ))}
      </div>
    );
  }

  if (rows.length === 0) return <EmptyState title={emptyTitle} description={emptyDescription} />;

  function toggleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("asc");
    } else {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    }
  }

  return (
    <div>
      <div className="ds-datatable-scroll" style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="ds-text-table-header"
                  style={{
                    textAlign: col.align ?? "left",
                    padding: "0.75rem 1rem",
                    color: "var(--text-secondary)",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--bg-muted)",
                    cursor: col.sortable ? "pointer" : undefined,
                    userSelect: "none",
                  }}
                  aria-sort={sortKey === col.key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                  onClick={() => col.sortable && toggleSort(col.key)}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                    {col.header}
                    {col.sortable && sortKey === col.key && (sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={rowKey(row)} style={{ borderBottom: "1px solid var(--border)" }}>
                {columns.map((col) => (
                  <td key={col.key} className="ds-text-table-cell" style={{ padding: "0.75rem 1rem", textAlign: col.align ?? "left", color: "var(--text-primary)" }}>
                    {col.render ? col.render(row) : String(col.accessor?.(row) ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {mobileCard && (
        <div className="ds-datatable-cards" style={{ display: "none", flexDirection: "column", gap: "0.75rem" }}>
          {sortedRows.map((row) => (
            <div key={rowKey(row)}>{mobileCard(row)}</div>
          ))}
        </div>
      )}
    </div>
  );
}
