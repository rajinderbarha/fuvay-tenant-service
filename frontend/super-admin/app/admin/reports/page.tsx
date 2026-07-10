"use client";
import { useEffect, useState } from "react";
import { adminAnalyticsApi } from "@/lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  COMPLETED: { background: "var(--success-bg)",     color: "var(--success-text)" },
  FAILED:    { background: "var(--danger-bg)",      color: "var(--danger-text)" },
  RUNNING:   { background: "var(--info-bg)",        color: "var(--info-text)" },
  PENDING:   { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
};

const btnBase: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius: 8, cursor: "pointer",
  fontFamily: "inherit", border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)",
};

export default function AdminReportsPage() {
  const [definitions, setDefinitions] = useState<any[]>([]);
  const [runs, setRuns]               = useState<any[]>([]);
  const [loading, setLoading]         = useState(true);
  const [running, setRunning]         = useState<string | null>(null);
  const [message, setMessage]         = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.listReports({});
      setDefinitions(r?.definitions ?? []);
      setRuns(r?.recent_runs?.items ?? []);
    } catch { }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function runReport(reportKey: string, exportFormat?: string) {
    setRunning(reportKey);
    setMessage("");
    try {
      const r = await adminAnalyticsApi.runReport({ report_key: reportKey, export_format: exportFormat });
      const result = r;
      if (result?.csv_content) {
        const blob = new Blob([result.csv_content], { type: "text/csv" });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href     = url;
        a.download = `${reportKey}_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        setMessage(`${reportKey}: exported ${result?.row_count ?? 0} rows`);
      } else {
        setMessage(`${reportKey}: ${result?.row_count ?? 0} rows (no export requested)`);
      }
      load();
    } catch (e: any) {
      setMessage(`Failed: ${e?.message ?? "unknown error"}`);
    } finally {
      setRunning(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Admin Reports</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Run and export platform reports. Sync export for up to 5,000 rows.</p>
      </div>

      {message && (
        <div style={{ background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: 10,
          padding: "12px 16px", fontSize: 13, color: "var(--info-text)" }}>
          {message}
        </div>
      )}

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Available Reports</h2>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[1,2,3].map(i => <div key={i} style={{ height: 56, background: "var(--surface-sunken)", borderRadius: 8 }} />)}
          </div>
        ) : definitions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>No reports available</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {definitions.map((def: any) => (
              <div key={def.report_key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{def.report_name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                    Key: {def.report_key} · Formats: {def.export_formats?.join(", ") ?? "json"}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button onClick={() => runReport(def.report_key)} disabled={running === def.report_key}
                    style={{ ...btnBase, opacity: running === def.report_key ? 0.5 : 1 }}>
                    {running === def.report_key ? "Running…" : "Run"}
                  </button>
                  {def.export_formats?.includes("csv") && (
                    <button onClick={() => runReport(def.report_key, "csv")} disabled={running === def.report_key}
                      style={{ ...btnBase, background: "var(--text-primary)", color: "var(--surface)", border: "none",
                        opacity: running === def.report_key ? 0.5 : 1 }}>
                      CSV
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {runs.length > 0 && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Recent Runs</h2>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {runs.map((run: any, idx: number) => (
              <div key={run.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "10px 0", borderBottom: idx < runs.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
                    {run.report_name ?? run.report_key}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                    {run.created_at ? new Date(run.created_at).toLocaleString() : "—"} · {run.row_count ?? 0} rows
                  </div>
                </div>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                  ...(STATUS_STYLE[run.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                  {run.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
