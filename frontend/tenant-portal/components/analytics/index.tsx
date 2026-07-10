"use client";
/**
 * Sprint 28 — Provider Analytics Shared Components (design-token edition)
 * All className removed — uses inline CSS with design token variables.
 */
import { useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string; value: string | number | null | undefined;
  unit?: string; loading?: boolean;
  severity?: "normal" | "warning" | "critical" | "success";
}
interface DateFilterProps {
  dateFrom: string; dateTo: string;
  onChange: (f: string, t: string) => void;
  loading?: boolean;
}
interface TableRow { [key: string]: unknown; }
interface TableProps {
  rows: TableRow[];
  columns: { key: string; label: string; numeric?: boolean }[];
  loading?: boolean; emptyText?: string;
}
interface AlertItem {
  type: string; severity: "info" | "warning" | "critical";
  count?: number; balance?: string; [key: string]: unknown;
}
interface AlertListProps { alerts: AlertItem[]; loading?: boolean; }

// ── Severity token mappings ────────────────────────────────────────────────────

const SEV_BORDER: Record<string, string> = { normal: "var(--border)", warning: "var(--warning)", critical: "var(--danger)", success: "var(--success)" };
const SEV_VALUE: Record<string, string>  = { normal: "var(--text-primary)", warning: "var(--warning-text)", critical: "var(--danger-text)", success: "var(--success-text)" };
const ALERT_BG:  Record<string, string>  = { critical: "var(--danger-bg)", warning: "var(--warning-bg)", info: "var(--info-bg)" };
const ALERT_BD:  Record<string, string>  = { critical: "var(--danger-border)", warning: "var(--warning-border)", info: "var(--info-border)" };
const ALERT_TX:  Record<string, string>  = { critical: "var(--danger-text)", warning: "var(--warning-text)", info: "var(--info-text)" };
const ALERT_IC:  Record<string, string>  = { critical: "🚨", warning: "⚠️", info: "ℹ️" };

// ── KPI Card ──────────────────────────────────────────────────────────────────

export function KpiCard({ label, value, unit, loading, severity = "normal" }: KpiCardProps) {
  return (
    <div style={{
      background: "var(--surface)", borderRadius: 12, padding: "16px 20px",
      border: `1px solid var(--border)`, borderLeft: `4px solid ${SEV_BORDER[severity]}`,
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
        color: "var(--text-tertiary)", marginBottom: 8 }}>{label}</div>
      {loading ? (
        <div style={{ height: 28, width: 64, borderRadius: 6, background: "var(--surface-sunken)" }}/>
      ) : (
        <div style={{ fontSize: 24, fontWeight: 700, color: SEV_VALUE[severity], lineHeight: 1 }}>
          {value == null ? <span style={{ color: "var(--text-tertiary)", fontSize: 14 }}>—</span> : value}
          {unit && value != null && <span style={{ fontSize: 13, fontWeight: 400, color: "var(--text-secondary)", marginLeft: 4 }}>{unit}</span>}
        </div>
      )}
    </div>
  );
}

// ── Date Filter ───────────────────────────────────────────────────────────────

export function DateFilter({ dateFrom, dateTo, onChange, loading }: DateFilterProps) {
  const inp: React.CSSProperties = {
    height: 34, padding: "0 10px", fontSize: 13, borderRadius: 8,
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontFamily: "inherit",
  };
  const lbl: React.CSSProperties = { fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={lbl}>From</span>
        <input type="date" value={dateFrom} onChange={e => onChange(e.target.value, dateTo)} style={inp} disabled={loading}/>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={lbl}>To</span>
        <input type="date" value={dateTo} onChange={e => onChange(dateFrom, e.target.value)} style={inp} disabled={loading}/>
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {[{ l: "7d", d: 7 }, { l: "30d", d: 30 }, { l: "90d", d: 90 }].map(({ l, d }) => (
          <button key={l} onClick={() => {
            const to = new Date(); const fr = new Date();
            fr.setDate(to.getDate() - d);
            onChange(fr.toISOString().slice(0, 10), to.toISOString().slice(0, 10));
          }} style={{ height: 30, padding: "0 10px", fontSize: 12, fontWeight: 600, borderRadius: 6,
            border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-secondary)",
            cursor: "pointer", fontFamily: "inherit" }}>{l}</button>
        ))}
      </div>
    </div>
  );
}

// ── Simple Table ──────────────────────────────────────────────────────────────

export function SimpleTable({ rows, columns, loading, emptyText = "No data" }: TableProps) {
  if (loading) return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {[1,2,3].map(i => <div key={i} style={{ height: 40, borderRadius: 6, background: "var(--surface-sunken)" }}/>)}
    </div>
  );
  if (!rows?.length) return (
    <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>{emptyText}</div>
  );
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
            {columns.map(c => (
              <th key={c.key} style={{ padding: "8px 14px", fontSize: 11, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-tertiary)",
                textAlign: c.numeric ? "right" : "left" }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
              {columns.map(c => (
                <td key={c.key} style={{ padding: "10px 14px", color: "var(--text-primary)",
                  textAlign: c.numeric ? "right" : "left",
                  fontFamily: c.numeric ? "'JetBrains Mono', monospace" : "inherit" }}>
                  {String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Alert List ────────────────────────────────────────────────────────────────

export function AlertList({ alerts, loading }: AlertListProps) {
  if (loading) return <div style={{ height: 80, borderRadius: 8, background: "var(--surface-sunken)" }}/>;
  if (!alerts?.length) return (
    <div style={{ textAlign: "center", padding: "24px 0", color: "var(--success-text)", fontSize: 13 }}>
      No active alerts — looking good!
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {alerts.map((alert, i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "12px 16px",
          borderRadius: 10, background: ALERT_BG[alert.severity] ?? ALERT_BG.info,
          border: `1px solid ${ALERT_BD[alert.severity] ?? ALERT_BD.info}` }}>
          <span style={{ fontSize: 16, flexShrink: 0 }}>{ALERT_IC[alert.severity] ?? "ℹ️"}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: ALERT_TX[alert.severity] ?? ALERT_TX.info,
              textTransform: "capitalize" }}>{alert.type.replace(/_/g, " ")}</div>
            {alert.count != null && <div style={{ fontSize: 12, color: ALERT_TX[alert.severity], marginTop: 2 }}>Count: {alert.count}</div>}
            {alert.balance != null && <div style={{ fontSize: 12, color: ALERT_TX[alert.severity], marginTop: 2 }}>Balance: {alert.balance}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Export Button ─────────────────────────────────────────────────────────────

interface ExportButtonProps {
  reportKey: string; filters?: Record<string, string>;
  onRun: (b: { report_key: string; filters?: Record<string, string>; export_format: string }) => Promise<{ csv_content?: string; row_count?: number }>;
  label?: string;
}

export function AnalyticsExportButton({ reportKey, filters, onRun, label = "Export CSV" }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleExport() {
    setLoading(true); setMessage("");
    try {
      const r = await onRun({ report_key: reportKey, filters, export_format: "csv" });
      if (r.csv_content) {
        const blob = new Blob([r.csv_content], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportKey}_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click(); URL.revokeObjectURL(url);
        setMessage(`Exported ${r.row_count ?? 0} rows`);
      } else {
        setMessage(`Report ready: ${r.row_count ?? 0} rows`);
      }
    } catch { setMessage("Export failed"); }
    finally { setLoading(false); }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <button onClick={handleExport} disabled={loading} style={{
        height: 36, padding: "0 16px", fontSize: 13, fontWeight: 600, borderRadius: 8,
        border: "none", cursor: loading ? "not-allowed" : "pointer",
        background: "var(--accent)", color: "white", fontFamily: "inherit", opacity: loading ? 0.6 : 1,
      }}>
        {loading ? "Exporting…" : label}
      </button>
      {message && <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{message}</span>}
    </div>
  );
}
