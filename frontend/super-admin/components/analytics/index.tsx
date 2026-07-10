"use client";
/**
 * Sprint 28 — Shared Analytics Components (design-token edition)
 * All className removed — uses inline CSS with design token variables.
 */
import { useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface KpiCardProps {
  label:    string;
  value:    string | number | null | undefined;
  unit?:    string;
  loading?: boolean;
  severity?: "normal" | "warning" | "critical" | "success";
}
export interface DateFilterProps {
  dateFrom: string; dateTo: string;
  onChange: (from: string, to: string) => void;
  loading?: boolean;
}
export interface BreakdownRow { [key: string]: unknown; }
export interface BreakdownTableProps {
  rows: BreakdownRow[];
  columns: { key: string; label: string; numeric?: boolean }[];
  loading?: boolean;
  emptyText?: string;
}
export interface AlertItem {
  type: string; severity: "info" | "warning" | "critical";
  count?: number; balance?: string; tenant_id?: string;
  [key: string]: unknown;
}
export interface AlertListProps { alerts: AlertItem[]; loading?: boolean; }

// ── Severity token mappings ────────────────────────────────────────────────────

const SEV_BORDER: Record<string, string> = {
  normal:   "var(--border)",
  warning:  "var(--warning)",
  critical: "var(--danger)",
  success:  "var(--success)",
};
const SEV_VALUE_COLOR: Record<string, string> = {
  normal:   "var(--text-primary)",
  warning:  "var(--warning-text)",
  critical: "var(--danger-text)",
  success:  "var(--success-text)",
};
const ALERT_BG: Record<string, string> = {
  critical: "var(--danger-bg)",
  warning:  "var(--warning-bg)",
  info:     "var(--info-bg)",
};
const ALERT_BORDER: Record<string, string> = {
  critical: "var(--danger-border)",
  warning:  "var(--warning-border)",
  info:     "var(--info-border)",
};
const ALERT_TEXT: Record<string, string> = {
  critical: "var(--danger-text)",
  warning:  "var(--warning-text)",
  info:     "var(--info-text)",
};
const ALERT_ICON: Record<string, string> = { critical: "🚨", warning: "⚠️", info: "ℹ️" };

// ── KPI Card ──────────────────────────────────────────────────────────────────

export function AnalyticsKpiCard({ label, value, unit, loading, severity = "normal" }: KpiCardProps) {
  return (
    <div style={{
      background: "var(--surface)", borderRadius: 12,
      padding: "16px 20px",
      boxShadow: "var(--shadow-sm)",
      borderLeft: `4px solid ${SEV_BORDER[severity] ?? SEV_BORDER.normal}`,
      border: `1px solid var(--border)`,
      borderLeftColor: SEV_BORDER[severity] ?? SEV_BORDER.normal,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
        textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 8 }}>
        {label}
      </div>
      {loading ? (
        <div style={{ height: 28, width: 64, borderRadius: 6,
          background: "var(--surface-sunken)", animation: "pulse 1.5s ease-in-out infinite" }}/>
      ) : (
        <div style={{ fontSize: 24, fontWeight: 700, color: SEV_VALUE_COLOR[severity] ?? SEV_VALUE_COLOR.normal, lineHeight: 1 }}>
          {value == null
            ? <span style={{ color: "var(--text-tertiary)", fontSize: 14 }}>—</span>
            : value}
          {unit && value != null && (
            <span style={{ fontSize: 13, fontWeight: 400, color: "var(--text-secondary)", marginLeft: 4 }}>{unit}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Date Filter Bar ───────────────────────────────────────────────────────────

export function AnalyticsDateFilter({ dateFrom, dateTo, onChange, loading }: DateFilterProps) {
  const inputStyle: React.CSSProperties = {
    height: 34, padding: "0 10px", fontSize: 13, borderRadius: 8,
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontFamily: "inherit", cursor: "pointer",
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600,
    textTransform: "uppercase", letterSpacing: "0.07em",
  };
  const presets = [{ label: "7d", days: 7 }, { label: "30d", days: 30 }, { label: "90d", days: 90 }];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={labelStyle}>From</span>
        <input type="date" value={dateFrom} onChange={e => onChange(e.target.value, dateTo)}
          style={inputStyle} disabled={loading}/>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={labelStyle}>To</span>
        <input type="date" value={dateTo} onChange={e => onChange(dateFrom, e.target.value)}
          style={inputStyle} disabled={loading}/>
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {presets.map(({ label, days }) => (
          <button key={label} onClick={() => {
            const to = new Date(); const from = new Date();
            from.setDate(to.getDate() - days);
            onChange(from.toISOString().slice(0, 10), to.toISOString().slice(0, 10));
          }} style={{
            height: 30, padding: "0 10px", fontSize: 12, fontWeight: 600,
            borderRadius: 6, border: "1px solid var(--border)",
            background: "var(--surface)", color: "var(--text-secondary)",
            cursor: "pointer", fontFamily: "inherit",
          }}>{label}</button>
        ))}
      </div>
    </div>
  );
}

// ── Breakdown Table ───────────────────────────────────────────────────────────

export function AnalyticsBreakdownTable({ rows, columns, loading, emptyText = "No data" }: BreakdownTableProps) {
  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {[1,2,3].map(i => (
          <div key={i} style={{ height: 40, borderRadius: 6, background: "var(--surface-sunken)" }}/>
        ))}
      </div>
    );
  }
  if (!rows?.length) {
    return (
      <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
        {emptyText}
      </div>
    );
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
            {columns.map(c => (
              <th key={c.key} style={{
                padding: "8px 14px", fontSize: 11, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.07em",
                color: "var(--text-tertiary)",
                textAlign: c.numeric ? "right" : "left",
              }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
              {columns.map(c => (
                <td key={c.key} style={{
                  padding: "10px 14px",
                  color: "var(--text-primary)",
                  textAlign: c.numeric ? "right" : "left",
                  fontFamily: c.numeric ? "'JetBrains Mono', monospace" : "inherit",
                }}>
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

// ── Operational Alert List ────────────────────────────────────────────────────

export function OperationalAlertList({ alerts, loading }: AlertListProps) {
  if (loading) {
    return <div style={{ height: 80, borderRadius: 8, background: "var(--surface-sunken)" }}/>;
  }
  if (!alerts?.length) {
    return (
      <div style={{ textAlign: "center", padding: "24px 0", color: "var(--success-text)", fontSize: 13 }}>
        No active alerts — all systems healthy.
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {alerts.map((alert, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "flex-start", gap: 12,
          padding: "12px 16px", borderRadius: 10,
          background: ALERT_BG[alert.severity] ?? ALERT_BG.info,
          border: `1px solid ${ALERT_BORDER[alert.severity] ?? ALERT_BORDER.info}`,
        }}>
          <span style={{ fontSize: 16, flexShrink: 0 }}>{ALERT_ICON[alert.severity] ?? "ℹ️"}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: ALERT_TEXT[alert.severity] ?? ALERT_TEXT.info,
              textTransform: "capitalize" }}>
              {alert.type.replace(/_/g, " ")}
            </div>
            {alert.count != null && (
              <div style={{ fontSize: 12, color: ALERT_TEXT[alert.severity], marginTop: 2 }}>Count: {alert.count}</div>
            )}
            {alert.balance != null && (
              <div style={{ fontSize: 12, color: ALERT_TEXT[alert.severity], marginTop: 2 }}>Balance: {alert.balance}</div>
            )}
            {alert.tenant_id && (
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontFamily: "'JetBrains Mono', monospace" }}>
                Tenant: {alert.tenant_id}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Export Button ─────────────────────────────────────────────────────────────

interface ExportButtonProps {
  reportKey: string;
  filters?: Record<string, string>;
  onRun: (body: { report_key: string; filters?: Record<string, string>; export_format: string }) => Promise<{ csv_content?: string; row_count?: number }>;
  label?: string;
}

export function AnalyticsExportButton({ reportKey, filters, onRun, label = "Export CSV" }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleExport() {
    setLoading(true); setMessage("");
    try {
      const result = await onRun({ report_key: reportKey, filters, export_format: "csv" });
      if (result.csv_content) {
        const blob = new Blob([result.csv_content], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportKey}_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click(); URL.revokeObjectURL(url);
        setMessage(`Exported ${result.row_count ?? 0} rows`);
      } else {
        setMessage(`Report ready: ${result.row_count ?? 0} rows`);
      }
    } catch {
      setMessage("Export failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <button onClick={handleExport} disabled={loading} style={{
        height: 36, padding: "0 16px", fontSize: 13, fontWeight: 600,
        borderRadius: 8, border: "none", cursor: loading ? "not-allowed" : "pointer",
        background: "var(--accent)", color: "white", fontFamily: "inherit",
        opacity: loading ? 0.6 : 1,
      }}>
        {loading ? "Exporting…" : label}
      </button>
      {message && <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{message}</span>}
    </div>
  );
}
