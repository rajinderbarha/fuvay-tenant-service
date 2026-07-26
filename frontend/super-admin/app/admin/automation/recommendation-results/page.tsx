"use client";

import { useEffect, useState } from "react";
import { recommendationApi, RecommendationResult } from "../../../../lib/api";

const STATUS_COLORS: Record<string, string> = {
  shown:        "#f3f4f6",
  accepted:     "#dcfce7",
  rejected:     "#fef2f2",
  auto_applied: "#dbeafe",
  ignored:      "#f3f4f6",
  failed:       "#fef2f2",
};

const CONTEXT_TYPES = [
  "admin_bulk_setup", "tenant_setup", "customer_booking", "ai_chat", "system_seed",
];

export default function RecommendationResultsPage() {
  const [results, setResults] = useState<RecommendationResult[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [contextFilter, setContextFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await recommendationApi.listResults({
        status: statusFilter || undefined,
        context_type: contextFilter || undefined,
        page_size: 50,
      });
      setResults(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [statusFilter, contextFilter]);

  const handleAccept = async (id: string) => {
    await recommendationApi.acceptResult(id);
    await load();
  };

  const handleReject = async (id: string) => {
    const reason = prompt("Rejection reason (optional):");
    await recommendationApi.rejectResult(id, reason ?? undefined);
    await load();
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>Recommendation Results</h1>
          <p style={{ color: "#6b7280", margin: "0.25rem 0 0" }}>
            Track recommendations shown, accepted, and rejected across all contexts ({total} total)
          </p>
        </div>
        <a href="/admin/automation/recommendation-rules"
          style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", color: "#4b5563", textDecoration: "none", fontSize: "0.875rem" }}>
          ← Back to Rules
        </a>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Statuses</option>
          {["shown", "accepted", "rejected", "auto_applied", "ignored", "failed"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={contextFilter} onChange={e => setContextFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Contexts</option>
          {CONTEXT_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {loading ? (
        <p style={{ color: "#6b7280" }}>Loading...</p>
      ) : results.length === 0 ? (
        <p style={{ color: "#9ca3af", textAlign: "center", padding: "3rem" }}>
          No recommendation results yet. Results appear when rules are evaluated.
        </p>
      ) : (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Context", "Entity Type", "Name / ID", "Confidence", "Explanation", "Status", "Created", "Actions"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map(res => (
                <tr key={res.id} style={{ borderBottom: "1px solid #f3f4f6", background: STATUS_COLORS[res.status] ?? "transparent" }}>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <div style={{ fontSize: "0.75rem", fontWeight: 600 }}>{res.context_type}</div>
                    {res.context_id && <div style={{ fontSize: "0.65rem", color: "#9ca3af", fontFamily: "monospace" }}>{res.context_id.slice(0, 8)}…</div>}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontFamily: "monospace" }}>{res.recommended_entity_type ?? "—"}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontFamily: "monospace" }}>
                    {res.recommended_entity_id?.slice(0, 8) ?? "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem" }}>
                    {res.confidence_score != null ? res.confidence_score.toFixed(2) : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#4b5563", maxWidth: "200px" }}>
                    {res.explanation ?? "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "9999px", background: STATUS_COLORS[res.status] }}>
                      {res.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.72rem", color: "#6b7280" }}>
                    {res.created_at ? new Date(res.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    {res.status === "shown" && (
                      <div style={{ display: "flex", gap: "0.4rem" }}>
                        <button onClick={() => handleAccept(res.id)}
                          style={{ fontSize: "0.7rem", color: "var(--success)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>Accept</button>
                        <button onClick={() => handleReject(res.id)}
                          style={{ fontSize: "0.7rem", color: "var(--danger)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>Reject</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
