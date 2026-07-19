"use client";
import React, { useMemo, useState } from "react";
import { PageHeader, Section } from "@serviceos/design-system";
import { DataTable, type DataTableColumn } from "@serviceos/design-system";
import { Button } from "@serviceos/design-system";
import { ReadinessTag } from "../widgets/ReadinessTag";
import type { ReadinessState } from "../../../lib/ux02/types";

/**
 * Reusable enterprise list-page pattern (UX-02).
 * Used by: Tenant List, Compliance Cases, Security Observations.
 *
 * MOCK_DESIGN_ONLY: filters/saved-views are client-side over fixture data.
 * Bulk actions here render a confirmation/impact-preview UI only — no
 * backend mutation is invoked.
 */
export interface ListFilterOption { key: string; label: string; values: string[]; }

export interface EnterpriseListPageProps<T> {
  title: string;
  description: string;
  readiness: ReadinessState;
  rows: T[];
  columns: DataTableColumn<T>[];
  rowKey: (row: T) => string;
  searchFields: (row: T) => string;
  filters?: ListFilterOption[];
  getFilterValue?: (row: T, key: string) => string;
  bulkActions?: { key: string; label: string }[];
  mobileCard?: (row: T) => React.ReactNode;
}

export function EnterpriseListPage<T>({
  title, description, readiness, rows, columns, rowKey, searchFields,
  filters = [], getFilterValue, bulkActions = [], mobileCard,
}: EnterpriseListPageProps<T>) {
  const [query, setQuery] = useState("");
  const [draftFilters, setDraftFilters] = useState<Record<string, string>>({});
  const [appliedFilters, setAppliedFilters] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkPreview, setBulkPreview] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (query && !searchFields(r).toLowerCase().includes(query.toLowerCase())) return false;
      for (const [k, v] of Object.entries(appliedFilters)) {
        if (v && getFilterValue && getFilterValue(r, k) !== v) return false;
      }
      return true;
    });
  }, [rows, query, appliedFilters, searchFields, getFilterValue]);

  function applyFilters() { setAppliedFilters(draftFilters); }
  function clearChip(key: string) {
    const next = { ...appliedFilters }; delete next[key];
    setAppliedFilters(next);
    setDraftFilters(next);
  }

  function toggleAll() {
    setSelected((s) => (s.size === filtered.length ? new Set() : new Set(filtered.map((r) => rowKey(r)))));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <PageHeader
        title={title}
        description={description}
        actions={<ReadinessTag readiness={readiness} />}
      />

      <Section title="Filters">
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <input
            aria-label="Search"
            placeholder="Search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)" }}
          />
          {filters.map((f) => (
            <select
              key={f.key}
              aria-label={f.label}
              value={draftFilters[f.key] ?? ""}
              onChange={(e) => setDraftFilters((d) => ({ ...d, [f.key]: e.target.value }))}
              style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)" }}
            >
              <option value="">{f.label}: Any</option>
              {f.values.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          ))}
          <Button size="sm" onClick={applyFilters}>Apply</Button>
        </div>
        {Object.entries(appliedFilters).filter(([, v]) => v).length > 0 && (
          <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
            {Object.entries(appliedFilters).filter(([, v]) => v).map(([k, v]) => (
              <button
                key={k}
                onClick={() => clearChip(k)}
                style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-full)", background: "var(--bg-muted)", color: "var(--text-primary)", padding: "0.25rem 0.625rem", fontSize: "0.75rem", cursor: "pointer" }}
              >
                {k}: {v} ×
              </button>
            ))}
          </div>
        )}
      </Section>

      {bulkActions.length > 0 && selected.size > 0 && (
        <Section title={`${selected.size} selected`}>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {bulkActions.map((a) => (
              <Button key={a.key} size="sm" variant="secondary" onClick={() => setBulkPreview(a.key)}>{a.label}</Button>
            ))}
          </div>
          {bulkPreview && (
            <div role="alertdialog" aria-label="Bulk action impact preview" style={{ marginTop: "0.75rem", padding: "1rem", border: "1px solid var(--warning-border)", background: "var(--warning-bg)", borderRadius: "var(--radius-md)", color: "var(--text-primary)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>Impact preview (design-only, no backend call)</p>
              <p style={{ margin: "0.25rem 0" }}>This action would apply to {selected.size} record(s). MOCK_DESIGN_ONLY — no mutation executes here.</p>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <Button size="sm" onClick={() => setBulkPreview(null)}>Confirm (mock)</Button>
                <Button size="sm" variant="ghost" onClick={() => setBulkPreview(null)}>Cancel</Button>
              </div>
            </div>
          )}
        </Section>
      )}

      <Section>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
          {bulkActions.length > 0 && (
            <label style={{ display: "flex", alignItems: "center", gap: "0.375rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              <input type="checkbox" checked={selected.size === filtered.length && filtered.length > 0} onChange={toggleAll} />
              Select all ({filtered.length})
            </label>
          )}
        </div>
        <DataTable columns={columns} rows={filtered} rowKey={rowKey} mobileCard={mobileCard} emptyDescription="No records match the current filters." />
      </Section>
    </div>
  );
}
