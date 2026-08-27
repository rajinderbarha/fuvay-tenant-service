"use client";
import { TableSurface } from "@serviceos/design-system";

import { useEffect, useState } from "react";
import Link from "next/link";
import { customerFlowApi, CustomerFlowConfig } from "../../../lib/api";
import { PageHeader } from "@serviceos/design-system";

const FLOW_TYPE_COLORS: Record<string, string> = {
  service_booking:     "#dbeafe",
  appointment_booking: "#dcfce7",
  lead_capture:        "#fef9c3",
  subscription_only:   "#f3e8ff",
};

export default function CustomerFlowOverviewPage() {
  const [configs, setConfigs] = useState<CustomerFlowConfig[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await customerFlowApi.adminListFlowConfigs();
      setConfigs(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader eyebrow="Catalog" title="Customer Flow Configuration"
        description={`Per-category booking flow types. Backend validates all catalog choices — AI cannot invent IDs. (${total} configured)`}
        actions={<Link href="/admin/customer-flow/drafts"
          style={{ padding: "var(--space-2) var(--space-4)", background: "var(--brand)", color: "var(--text-on-brand)", borderRadius: "var(--radius-md)", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
          View Booking Drafts
        </Link>} />

      {/* Flow type legend */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {Object.entries(FLOW_TYPE_COLORS).map(([type, color]) => (
          <span key={type} style={{ fontSize: "0.75rem", padding: "0.2rem 0.6rem", borderRadius: "9999px", background: color, fontWeight: 500 }}>
            {type.replace(/_/g, " ")}
          </span>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "#6b7280" }}>Loading...</p>
      ) : configs.length === 0 ? (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f9fafb", borderRadius: "0.5rem" }}>
          <p style={{ color: "#9ca3af", fontSize: "0.9rem" }}>
            No customer flow configs configured. Bookings will default to service_booking flow.
          </p>
          <p style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: "0.5rem" }}>
            Configure flow types via Admin → Service Catalog → Category Flow Config.
          </p>
        </div>
      ) : (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", overflow: "hidden" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Category ID", "Flow Type", "Component Key", "Engine Key", "Required Steps", "Optional Steps"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {configs.map((cfg, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.72rem", fontFamily: "monospace", color: "#6b7280" }}>
                    {cfg.category_id.slice(0, 8)}…
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem", borderRadius: "9999px", background: FLOW_TYPE_COLORS[cfg.customer_flow_type] ?? "#f3f4f6", fontWeight: 500 }}>
                      {cfg.customer_flow_type}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem", fontFamily: "monospace" }}>{cfg.frontend_component_key}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem", fontFamily: "monospace" }}>{cfg.primary_engine_key}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#4b5563" }}>
                    {cfg.required_steps?.join(", ") ?? "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#9ca3af" }}>
                    {cfg.optional_steps?.join(", ") ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>
      )}

      {/* Architecture note */}
      <div style={{ marginTop: "1.5rem", background: "var(--accent-muted)", border: "1px solid var(--brand)", borderRadius: "0.5rem", padding: "1rem" }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--brand-hover)", margin: "0 0 0.5rem" }}>
          Customer Flow Architecture
        </h3>
        <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.8rem", color: "var(--brand-hover)" }}>
          <li>AI can guide conversation — backend validates all entity IDs</li>
          <li>Customer sees only active categories, services, brands, options, and issue types</li>
          <li>Draft confirms only after service selection + contact info validation</li>
          <li>Flow type determined by category config, not by customer or AI</li>
        </ul>
      </div>
    </div>
  );
}
