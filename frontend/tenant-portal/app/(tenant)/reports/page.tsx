"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { providerAnalyticsApi, ServiceOSError } from "../../../lib/api";
import {
  Download, Play, FileText, Filter, X, RefreshCw, AlertCircle, ChevronRight,
} from "lucide-react";
import { Pagination } from "@serviceos/design-system";

/**
 * Reports.
 *
 * Each definition declares `allowed_filters`, and the run endpoint validates
 * against that list and now genuinely applies them. This page builds its filter
 * controls FROM that declaration, so it can never offer a filter the server
 * would reject — and never hides one the server supports.
 */

// ── Types (the API's real shapes, not `any`) ─────────────────────────────────
interface FilterOption { value: string; label: string }

interface ReportFilterOptions {
  offerings: FilterOption[];
  categories: FilterOption[];
  staff: FilterOption[];
  statuses: FilterOption[];
}

interface ReportDefinition {
  report_key: string;
  report_name: string;
  scope: string;
  allowed_filters: string[];
  export_formats: string[];
}

interface ReportRun {
  id: string;
  report_key: string;
  report_name: string | null;
  status: string;
  row_count: number | string | null;
  filters: Record<string, string> | null;
  result_summary: { row_count?: number; columns?: string[] } | null;
  export_format: string | null;
  failure_reason: string | null;
  created_at: string | null;
  completed_at: string | null;
}

interface ReportsResponse {
  definitions: ReportDefinition[];
  recent_runs: { items: ReportRun[]; total: number };
  filter_options?: ReportFilterOptions;
}

interface RunResult {
  id: string;
  report_key: string;
  status: string;
  row_count: number | string;
  preview: Record<string, unknown>[];
  csv_content?: string | null;
  generated_at: string;
}

const RUNS_PAGE = 10;

/** Status arrives lower-case (`completed`), so matching must be case-insensitive.
 *  Keying on UPPERCASE meant every run fell through to the neutral grey style
 *  and a failed run looked exactly like a successful one. */
const STATUS_STYLE: Record<string, React.CSSProperties> = {
  completed: { background: "var(--success-bg)", color: "var(--success-text)" },
  failed:    { background: "var(--danger-bg)",  color: "var(--danger-text)" },
  running:   { background: "var(--info-bg)",    color: "var(--info-text)" },
  pending:   { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
};
const statusStyle = (s: string | null | undefined) =>
  STATUS_STYLE[(s ?? "").toLowerCase()] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" };

const FILTER_LABELS: Record<string, string> = {
  date_from: "From", date_to: "To", status: "Job status",
  offering_id: "Service", category_id: "Category", staff_member_id: "Technician",
  payment_status: "Payment status", commission_status: "Commission status",
};

const PAYMENT_STATUSES: FilterOption[] = [
  { value: "pending", label: "Pending" },
  { value: "paid", label: "Paid" },
  { value: "partially_paid", label: "Partially paid" },
  { value: "failed", label: "Failed" },
  { value: "refunded", label: "Refunded" },
];
const COMMISSION_STATUSES: FilterOption[] = [
  { value: "pending", label: "Pending" },
  { value: "charged", label: "Charged" },
  { value: "waived", label: "Waived" },
];

const btnBase: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius: "var(--radius-md)", cursor: "pointer",
  fontFamily: "inherit", border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)",
  display: "inline-flex", alignItems: "center", gap: 6,
};
const inputBase: React.CSSProperties = {
  padding: "6px 10px", fontSize: 12.5, borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)", background: "var(--surface)",
  color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
};

export default function ProviderReportsPage() {
  const [data, setData] = useState<ReportsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "info" | "danger"; text: string } | null>(null);
  const [openFilters, setOpenFilters] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, Record<string, string>>>({});
  const [result, setResult] = useState<RunResult | null>(null);
  const [runsPage, setRunsPage] = useState(0);

  const load = useCallback(async (offset = 0) => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await providerAnalyticsApi.listReports({ limit: RUNS_PAGE, offset });
      setData(r as unknown as ReportsResponse);
    } catch (e: unknown) {
      // Never swallow this. The previous `catch {}` left the page showing
      // "No reports available", which is indistinguishable from a genuine
      // empty list — an outage looked like an empty product.
      setData(null);
      setLoadError(e instanceof ServiceOSError ? e.message : "We couldn't load your reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(runsPage * RUNS_PAGE); }, [load, runsPage]);

  const options = data?.filter_options;

  const optionsFor = useCallback((filterKey: string): FilterOption[] => {
    switch (filterKey) {
      case "offering_id": return options?.offerings ?? [];
      case "category_id": return options?.categories ?? [];
      case "staff_member_id": return options?.staff ?? [];
      case "status": return options?.statuses ?? [];
      case "payment_status": return PAYMENT_STATUSES;
      case "commission_status": return COMMISSION_STATUSES;
      default: return [];
    }
  }, [options]);

  const setFilter = (reportKey: string, key: string, value: string) =>
    setFilters(prev => {
      const next = { ...(prev[reportKey] ?? {}) };
      if (value) next[key] = value; else delete next[key];
      return { ...prev, [reportKey]: next };
    });

  const activeCount = (reportKey: string) => Object.keys(filters[reportKey] ?? {}).length;

  async function runReport(def: ReportDefinition, exportFormat?: string) {
    setRunning(def.report_key);
    setMessage(null);
    setResult(null);
    try {
      const applied = filters[def.report_key] ?? {};
      const r = await providerAnalyticsApi.runReport({
        report_key: def.report_key,
        ...(Object.keys(applied).length ? { filters: applied } : {}),
        ...(exportFormat ? { export_format: exportFormat } : {}),
      }) as unknown as RunResult;

      if (exportFormat === "csv") {
        if (!r.csv_content) {
          // A completed run with no file is a real outcome (no rows matched);
          // say so rather than downloading an empty file.
          setMessage({ tone: "info", text: "Nothing to export — no rows matched these filters." });
        } else {
          const blob = new Blob([r.csv_content], { type: "text/csv;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${def.report_key}_${new Date().toISOString().slice(0, 10)}.csv`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
          setMessage({ tone: "info", text: `Exported ${r.row_count} rows.` });
        }
      } else {
        setResult(r);
        setMessage({ tone: "info", text: `${def.report_name}: ${r.row_count} rows.` });
      }
      void load(runsPage * RUNS_PAGE);
    } catch (e: unknown) {
      setMessage({
        tone: "danger",
        text: e instanceof ServiceOSError
          ? `${e.message}${e.resolution ? ` ${e.resolution}` : ""}`
          : "The report could not be run.",
      });
    } finally {
      setRunning(null);
    }
  }

  const definitions = data?.definitions ?? [];
  const runs = data?.recent_runs?.items ?? [];
  const runsTotal = data?.recent_runs?.total ?? 0;

  return (
    <TenantLayout activeNav="reports">
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Reports</h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Export your business data. Reports include only your own records.
            </p>
          </div>
          <button style={btnBase} onClick={() => void load(runsPage * RUNS_PAGE)} disabled={loading}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {loadError && (
          <div role="alert" style={{
            background: "var(--danger-bg)", border: "1px solid var(--danger-border, var(--border))",
            borderRadius: 10, padding: "12px 16px", fontSize: 13, color: "var(--danger-text)",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <AlertCircle size={15} /> {loadError}
            <button style={{ ...btnBase, marginLeft: "auto" }} onClick={() => void load()}>Try again</button>
          </div>
        )}

        {message && (
          <div style={{
            background: message.tone === "danger" ? "var(--danger-bg)" : "var(--info-bg)",
            border: `1px solid ${message.tone === "danger" ? "var(--danger-border, var(--border))" : "var(--info-border)"}`,
            borderRadius: 10, padding: "12px 16px", fontSize: 13,
            color: message.tone === "danger" ? "var(--danger-text)" : "var(--info-text)",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            {message.text}
            <button aria-label="Dismiss" onClick={() => setMessage(null)}
              style={{ ...btnBase, marginLeft: "auto", padding: "2px 8px" }}>
              <X size={12} />
            </button>
          </div>
        )}

        {/* ── Available reports ───────────────────────────────────────────── */}
        <section style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)", padding: 20,
        }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Available reports
          </h2>

          {loading && !data ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[1, 2, 3].map(i => (
                <div key={i} style={{ height: 56, background: "var(--surface-sunken)", borderRadius: "var(--radius-md)" }} />
              ))}
            </div>
          ) : definitions.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
              {loadError ? "Reports could not be loaded." : "No reports available for your account."}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {definitions.map(def => {
                const isOpen = openFilters === def.report_key;
                const n = activeCount(def.report_key);
                const busy = running === def.report_key;
                // Dates are rendered as a pair; the rest come straight from
                // what this report declares.
                const selectable = def.allowed_filters.filter(f => f !== "date_from" && f !== "date_to");
                const hasDates = def.allowed_filters.includes("date_from") || def.allowed_filters.includes("date_to");

                return (
                  <div key={def.report_key} style={{ border: "1px solid var(--border)", borderRadius: 10 }}>
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "12px 16px", gap: 12, flexWrap: "wrap",
                    }}>
                      <div style={{ minWidth: 200 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
                          <FileText size={13} style={{ color: "var(--text-tertiary)" }} />
                          {def.report_name}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                          {def.allowed_filters.length} filter{def.allowed_filters.length === 1 ? "" : "s"}
                          {n > 0 ? ` · ${n} applied` : ""}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <button
                          style={{ ...btnBase, ...(n > 0 ? { borderColor: "var(--info-text)", color: "var(--info-text)" } : {}) }}
                          onClick={() => setOpenFilters(isOpen ? null : def.report_key)}
                          aria-expanded={isOpen}
                        >
                          <Filter size={13} /> Filters{n > 0 ? ` (${n})` : ""}
                        </button>
                        <button onClick={() => void runReport(def)} disabled={busy}
                          style={{ ...btnBase, opacity: busy ? 0.5 : 1, cursor: busy ? "not-allowed" : "pointer" }}>
                          <Play size={13} /> {busy ? "Running…" : "Run"}
                        </button>
                        {/* Only formats the server can actually produce. */}
                        {def.export_formats.map(fmt => (
                          <button key={fmt} onClick={() => void runReport(def, fmt)} disabled={busy}
                            style={{
                              ...btnBase, background: "var(--text-primary)", color: "var(--surface)",
                              border: "none", opacity: busy ? 0.5 : 1, cursor: busy ? "not-allowed" : "pointer",
                            }}>
                            <Download size={13} /> {fmt.toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </div>

                    {isOpen && (
                      <div style={{
                        borderTop: "1px solid var(--border)", padding: "12px 16px",
                        display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end",
                        background: "var(--surface-sunken)",
                      }}>
                        {hasDates && (
                          <>
                            <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                              <div style={{ marginBottom: 4 }}>{FILTER_LABELS.date_from}</div>
                              <input type="date" style={inputBase}
                                value={filters[def.report_key]?.date_from ?? ""}
                                onChange={e => setFilter(def.report_key, "date_from", e.target.value)} />
                            </label>
                            <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                              <div style={{ marginBottom: 4 }}>{FILTER_LABELS.date_to}</div>
                              <input type="date" style={inputBase}
                                value={filters[def.report_key]?.date_to ?? ""}
                                onChange={e => setFilter(def.report_key, "date_to", e.target.value)} />
                            </label>
                          </>
                        )}
                        {selectable.map(key => {
                          const opts = optionsFor(key);
                          return (
                            <label key={key} style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                              <div style={{ marginBottom: 4 }}>{FILTER_LABELS[key] ?? key.replace(/_/g, " ")}</div>
                              <select style={{ ...inputBase, minWidth: 150 }}
                                value={filters[def.report_key]?.[key] ?? ""}
                                onChange={e => setFilter(def.report_key, key, e.target.value)}>
                                <option value="">All</option>
                                {opts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                              </select>
                            </label>
                          );
                        })}
                        {n > 0 && (
                          <button style={btnBase}
                            onClick={() => setFilters(prev => ({ ...prev, [def.report_key]: {} }))}>
                            Clear
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Preview of the last run ─────────────────────────────────────── */}
        {result && result.preview?.length > 0 && (
          <section style={{
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)", padding: 20,
          }}>
            <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 4px" }}>
              Preview
            </h2>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
              First {result.preview.length} of {result.row_count} rows. Export for the full set.
            </p>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
                <thead>
                  <tr>
                    {Object.keys(result.preview[0]).map(c => (
                      <th key={c} style={{
                        textAlign: "left", padding: "6px 10px", borderBottom: "1px solid var(--border)",
                        color: "var(--text-secondary)", fontWeight: 600, whiteSpace: "nowrap",
                      }}>{c.replace(/_/g, " ")}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.preview.map((row, i) => (
                    <tr key={i}>
                      {Object.keys(result.preview[0]).map(c => (
                        <td key={c} style={{
                          padding: "6px 10px", borderBottom: "1px solid var(--border)",
                          color: "var(--text-primary)", whiteSpace: "nowrap",
                        }}>{row[c] == null ? "—" : String(row[c])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
          </section>
        )}

        {/* ── Recent runs ─────────────────────────────────────────────────── */}
        <section style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)", padding: 20,
        }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Recent runs {runsTotal > 0 ? `(${runsTotal})` : ""}
          </h2>
          {runs.length === 0 ? (
            <div style={{ textAlign: "center", padding: "24px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
              No reports have been run yet.
            </div>
          ) : (
            <>
              <div>
                {runs.map((run, idx) => {
                  const applied = Object.entries(run.filters ?? {}).filter(([, v]) => v);
                  return (
                    <div key={run.id} style={{
                      display: "flex", alignItems: "flex-start", justifyContent: "space-between",
                      padding: "10px 0", gap: 12,
                      borderBottom: idx < runs.length - 1 ? "1px solid var(--border)" : "none",
                    }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
                          {run.report_name ?? run.report_key}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                          {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                          {" · "}{run.row_count ?? 0} rows
                          {run.export_format ? ` · ${run.export_format.toUpperCase()}` : ""}
                        </div>
                        {/* What was actually asked for — otherwise two runs of
                            the same report are indistinguishable. */}
                        {applied.length > 0 && (
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 3, display: "flex", gap: 6, flexWrap: "wrap" }}>
                            {applied.map(([k, v]) => (
                              <span key={k} style={{
                                border: "1px solid var(--border)", borderRadius: 999,
                                padding: "1px 8px", background: "var(--surface-sunken)",
                              }}>{FILTER_LABELS[k] ?? k.replace(/_/g, " ")}: {String(v)}</span>
                            ))}
                          </div>
                        )}
                        {/* A failed run used to show a grey badge and no reason
                            at all. */}
                        {run.failure_reason && (
                          <div style={{ fontSize: 11, color: "var(--danger-text)", marginTop: 3 }}>
                            {run.failure_reason.replace(/_/g, " ").toLowerCase()}
                          </div>
                        )}
                      </div>
                      <span style={{
                        fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                        whiteSpace: "nowrap", ...statusStyle(run.status),
                      }}>
                        {(run.status ?? "unknown").replace(/_/g, " ")}
                      </span>
                    </div>
                  );
                })}
              </div>
              <Pagination page={runsPage + 1} pageSize={RUNS_PAGE} total={runsTotal}
                onPage={target => setRunsPage(target - 1)} itemLabel="report runs" />
            </>
          )}
        </section>
      </div>
    </TenantLayout>
  );
}
