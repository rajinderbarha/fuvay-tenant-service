"use client";
/**
 * DESIGN PHASE UX-03 — shared list-page pattern (mirrors UX-02's
 * EnterpriseListPage, generalized for tenant-portal use: filters, search,
 * DataTable, empty/loading/error states). Reused across Jobs, Bookings,
 * Customers, Complaints, Team, etc. rather than rebuilt per module.
 */
import React, { useMemo, useState } from "react";
import { PageHeader, DataTable, type DataTableColumn } from "@serviceos/design-system";

export interface TenantListFilter {
  id: string;
  label: string;
  options: { value: string; label: string }[];
}

export function TenantListPage<T>({
  title,
  description,
  actions,
  columns,
  rows,
  rowKey,
  loading,
  error,
  emptyTitle,
  emptyDescription,
  searchable,
  searchPredicate,
  mobileCard,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  searchable?: boolean;
  searchPredicate?: (row: T, query: string) => boolean;
  mobileCard?: (row: T) => React.ReactNode;
}) {
  const [query, setQuery] = useState("");

  const filteredRows = useMemo(() => {
    if (!searchable || !query.trim() || !searchPredicate) return rows;
    return rows.filter((r) => searchPredicate(r, query.trim().toLowerCase()));
  }, [rows, query, searchable, searchPredicate]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <PageHeader title={title} description={description} actions={actions} />
      {searchable && (
        <input
          aria-label={`Search ${title}`}
          placeholder={`Search ${title.toLowerCase()}…`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", maxWidth: "24rem" }}
        />
      )}
      <DataTable
        columns={columns}
        rows={filteredRows}
        rowKey={rowKey}
        loading={loading}
        error={error}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        mobileCard={mobileCard}
      />
    </div>
  );
}
