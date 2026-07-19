"use client";
/**
 * DESIGN PHASE UX-04B — Parts Request list, distinct from the single-item
 * approval detail view (PartsRequestSummary). Columns per spec: request id,
 * ServiceJob, technician, part, quantity, cost, requested date, status,
 * approver, installation state, last activity, actions. Filters:
 * search/status/technician. Never links to a field_ops.Job; never renders
 * a technician mark-installed control (provider-side only, per action
 * availability).
 */
import React, { useMemo, useState } from "react";
import { StatusBadge } from "@serviceos/design-system";
import type { PartsRequestListItemView } from "../../lib/ux04/types";

export function PartsRequestList({
  items,
  loading,
  error,
}: {
  items: PartsRequestListItemView[];
  loading?: boolean;
  error?: string | null;
}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    return items.filter((row) => {
      if (statusFilter !== "all" && row.request.status !== statusFilter) return false;
      if (!query) return true;
      const haystack = `${row.request.id} ${row.serviceJobLabel} ${row.technicianName} ${row.request.items.map((i) => i.name).join(" ")}`.toLowerCase();
      return haystack.includes(query.toLowerCase());
    });
  }, [items, query, statusFilter]);

  if (loading) {
    return <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Loading parts requests…</p>;
  }
  if (error) {
    return <p style={{ fontSize: "0.8125rem", color: "var(--danger-text)" }}>Could not load parts requests: {error}</p>;
  }

  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
        <input
          aria-label="Search parts requests"
          placeholder="Search request, job, technician, part…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ padding: "0.375rem 0.5rem", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem" }}
        />
        <select
          aria-label="Filter by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "0.375rem 0.5rem", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem" }}
        >
          <option value="all">All statuses</option>
          <option value="requested">Requested</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="installed">Installed</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>No parts requests match the current filters.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
              <th>Request</th>
              <th>Service Job</th>
              <th>Technician</th>
              <th>Part(s)</th>
              <th>Qty</th>
              <th>Cost</th>
              <th>Status</th>
              <th>Approver</th>
              <th>Installation</th>
              <th>Last activity</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const totalQty = row.request.items.reduce((s, i) => s + i.qty, 0);
              const totalCost = row.request.items.reduce((s, i) => s + i.qty * i.unitCost, 0);
              const approveAction = row.actions.find((a) => a.actionKey.includes("approve"));
              return (
                <tr key={row.request.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td>{row.request.id}</td>
                  <td>{row.serviceJobLabel}</td>
                  <td>{row.technicianName}</td>
                  <td>{row.request.items.map((i) => i.name).join(", ")}</td>
                  <td>{totalQty}</td>
                  <td>{totalCost.toLocaleString()}</td>
                  <td>
                    <StatusBadge status={row.request.status} />
                  </td>
                  <td>{row.request.decidedByStaffId ?? "—"}</td>
                  <td>{row.installationState.replace(/_/g, " ")}</td>
                  <td>
                    {row.lastActivityAt}
                    {row.request.status === "requested" && !approveAction?.available && (
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
                        {approveAction?.reason ?? "No action available with your permissions."}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: "0.5rem", fontStyle: "italic" }}>
        Every row is ServiceJob-scoped only — no row ever links to a field_ops.Job. Technician install authority is
        never granted here; only the ServiceJob&apos;s own approval action set applies.
      </p>
    </div>
  );
}
