"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { setupTemplateApi, ServiceSetupTemplateRun34F } from "../../../../../../lib/api";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  completed_with_errors: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

export default function TemplateRunsPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const [runs, setRuns] = useState<ServiceSetupTemplateRun34F[]>([]);
  const [selected, setSelected] = useState<ServiceSetupTemplateRun34F | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await setupTemplateApi.listRuns(templateId);
      setRuns(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [templateId]);

  const handleSelectRun = async (runId: string) => {
    const detail = await setupTemplateApi.getRunDetail(runId);
    setSelected(detail);
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: "900px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <a href={`/admin/service-setup/templates/${templateId}`}
          style={{ color: "#6b7280", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Back to Template
        </a>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "0.5rem 0 0" }}>Apply Runs</h1>
        <p style={{ color: "#6b7280", margin: "0.25rem 0 0" }}>History of template applications</p>
      </div>

      {loading ? (
        <p style={{ color: "#6b7280" }}>Loading runs...</p>
      ) : runs.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No runs yet. Apply the template from the detail page.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: "1rem" }}>
          <div>
            {runs.map(run => (
              <div key={run.id}
                onClick={() => handleSelectRun(run.id)}
                style={{
                  background: selected?.id === run.id ? "#eff6ff" : "#fff",
                  border: `1px solid ${selected?.id === run.id ? "#93c5fd" : "#e5e7eb"}`,
                  borderRadius: "0.5rem", padding: "1rem", cursor: "pointer", marginBottom: "0.75rem",
                }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#6b7280" }}>
                    {run.id.slice(0, 8)}…
                  </span>
                  <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "9999px" }}
                    className={STATUS_COLORS[run.status] ?? "bg-gray-100"}>
                    {run.status}
                  </span>
                </div>
                <div style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
                  <span style={{ color: "#4b5563" }}>Scope: {run.target_scope}</span>
                  {run.summary_json && (
                    <span style={{ marginLeft: "0.75rem", color: "#6b7280" }}>
                      created:{(run.summary_json as Record<string, number>).created ?? 0} / errors:{(run.summary_json as Record<string, number>).errors ?? 0}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.25rem" }}>
                  {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                <h2 style={{ fontWeight: 700, fontSize: "0.95rem", margin: 0 }}>Run Detail</h2>
                <button onClick={() => setSelected(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", fontSize: "1.2rem" }}>×</button>
              </div>
              <pre style={{ fontSize: "0.72rem", background: "#f9fafb", borderRadius: "0.375rem", padding: "0.75rem", overflow: "auto", maxHeight: "400px" }}>
                {JSON.stringify(selected, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
