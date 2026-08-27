"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { setupTemplateApi, ServiceSetupTemplateRun34F } from "../../../../../../lib/api";
import { PageHeader } from "@serviceos/design-system";
import { Badge, Btn } from "../../../../../../components/shared/ui";

const statusVariant = (status: string): "info" | "success" | "warning" | "danger" | "muted" => {
  if (status === "completed") return "success";
  if (status === "completed_with_errors") return "warning";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  return "muted";
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
    <div style={{ maxWidth: 1000, display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <PageHeader
        title="Template Apply Runs"
        description="History and execution detail for template applications."
        eyebrow="Service Setup"
        actions={<Link href={`/admin/service-setup/templates/${templateId}`}><Btn variant="secondary" size="sm">Back to Template</Btn></Link>}
      />

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading runs...</p>
      ) : runs.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>No runs yet. Apply the template from the detail page.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: "1rem" }}>
          <div>
            {runs.map(run => (
              <div key={run.id} role="button" tabIndex={0}
                onClick={() => handleSelectRun(run.id)}
                onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); handleSelectRun(run.id); } }}
                style={{
                  background: selected?.id === run.id ? "var(--accent-muted)" : "var(--surface)",
                  border: `1px solid ${selected?.id === run.id ? "var(--accent)" : "var(--border)"}`,
                  borderRadius: "var(--radius-lg)", padding: "var(--space-4)", cursor: "pointer", marginBottom: "var(--space-3)",
                }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
                    {run.id.slice(0, 8)}…
                  </span>
                  <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                </div>
                <div style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Scope: {run.target_scope}</span>
                  {run.summary_json && (
                    <span style={{ marginLeft: "0.75rem", color: "var(--text-tertiary)" }}>
                      created:{(run.summary_json as Record<string, number>).created ?? 0} / errors:{(run.summary_json as Record<string, number>).errors ?? 0}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.25rem" }}>
                  {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                <h2 style={{ fontWeight: 700, fontSize: "0.95rem", margin: 0 }}>Run Detail</h2>
                <button type="button" aria-label="Close run detail" onClick={() => setSelected(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: "1.2rem" }}>×</button>
              </div>
              <pre style={{ fontSize: "0.72rem", background: "var(--surface-sunken)", color: "var(--text-secondary)", borderRadius: "var(--radius-md)", padding: "var(--space-3)", overflow: "auto", maxHeight: "400px" }}>
                {JSON.stringify(selected, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
