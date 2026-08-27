"use client";
import { TableSurface } from "@serviceos/design-system";

import { useEffect, useState } from "react";
import Link from "next/link";
import { customerFlowApi, CustomerBookingDraft } from "../../../../lib/api";
import { PageHeader } from "@serviceos/design-system";
import { Btn } from "../../../../components/shared/ui";

const STATUS_COLORS: Record<string, string> = {
  draft:     "#f3f4f6",
  estimated: "#fef9c3",
  confirmed: "#dcfce7",
  cancelled: "#fef2f2",
};

const FLOW_TYPES = ["service_booking", "appointment_booking", "lead_capture", "subscription_only"];
const STATUSES   = ["draft", "estimated", "confirmed", "cancelled"];

export default function CustomerDraftsPage() {
  const [drafts, setDrafts] = useState<CustomerBookingDraft[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [flowFilter, setFlowFilter] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await customerFlowApi.adminListDrafts({
        status:    statusFilter || undefined,
        flow_type: flowFilter   || undefined,
        page_size: 50,
      });
      setDrafts(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [statusFilter, flowFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader
        title="Customer Booking Drafts"
        description={`All customer booking drafts across every configured flow (${total} total).`}
        eyebrow="Customer Flow"
        actions={<Link href="/admin/customer-flow"><Btn variant="secondary" size="sm">Flow Configs</Btn></Link>}
      />

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={flowFilter} onChange={e => setFlowFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Flow Types</option>
          {FLOW_TYPES.map(f => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>

      {loading ? (
        <p style={{ color: "#6b7280" }}>Loading...</p>
      ) : drafts.length === 0 ? (
        <p style={{ color: "#9ca3af", textAlign: "center", padding: "3rem" }}>No booking drafts found.</p>
      ) : (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", overflow: "hidden" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Draft ID", "Flow", "Customer", "Service", "City", "Estimate", "Status", "Created", "Actions"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {drafts.map(d => (
                <tr key={d.id} style={{ borderBottom: "1px solid #f3f4f6", background: STATUS_COLORS[d.status] ?? "transparent" }}>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.72rem", fontFamily: "monospace", color: "#6b7280" }}>
                    {d.id.slice(0, 8)}…
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem" }}>{d.flow_type}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>
                    <div>{d.customer_name ?? "—"}</div>
                    {d.customer_phone && <div style={{ fontSize: "0.7rem", color: "#9ca3af" }}>{d.customer_phone}</div>}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.72rem", fontFamily: "monospace", color: "#6b7280" }}>
                    {d.service_id ? d.service_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>{d.city ?? "—"}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>
                    {d.estimate_min != null
                      ? `${d.estimate_currency} ${d.estimate_min}–${d.estimate_max}`
                      : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "9999px", background: STATUS_COLORS[d.status] }}>
                      {d.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.72rem", color: "#6b7280" }}>
                    {d.created_at ? new Date(d.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <Link href={`/admin/customer-flow/drafts/${d.id}`}
                      style={{ fontSize: "0.72rem", color: "#1e3a5f", textDecoration: "none" }}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>
      )}
    </div>
  );
}
