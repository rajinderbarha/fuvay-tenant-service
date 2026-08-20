"use client";
/**
 * The health engine's OUTPUT.
 *
 * The console could previously configure formulas, components, penalties, bands
 * and weights — and then had no way to see a single score any of it produced.
 * Health bands gate commission and bookability, so an admin editing a formula
 * was changing money and visibility with no feedback at all. This tab is the
 * missing half: which targets scored what, worst first, with the component
 * breakdown that explains the number.
 *
 * Everything here is paged and filtered server-side; the table never holds more
 * than one page of rows however many targets the platform has scored.
 */
import React, { useCallback, useState } from "react";
import { AlertTriangle, Gauge } from "lucide-react";
import { Card, Btn, Badge, Spinner, Select, Pagination, EmptyState } from "../../../components/shared/ui";
import { trustQualityApi, TQ_ENUMS, HealthScoreRow, HealthRule } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";

const PAGE_SIZE = 25;

/** Band colours mirror the seeded band keys; anything unknown falls back to muted. */
const BAND_TONE: Record<string, "success" | "info" | "warning" | "danger" | "muted"> = {
  platinum: "success", gold: "success", silver: "info", bronze: "warning",
  at_risk: "danger", critical: "danger", suspended: "danger",
};

export function ScoresTab({ formulas }: { formulas: HealthRule[] }) {
  const [page, setPage] = useState(1);
  const [targetType, setTargetType] = useState("");
  const [band, setBand] = useState("");
  const [formulaId, setFormulaId] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const scores = useApi(
    useCallback(() => trustQualityApi.listHealthScores({
      target_type: targetType || undefined,
      band_key: band || undefined,
      formula_id: formulaId || undefined,
      limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
    }), [targetType, band, formulaId, page]),
    [targetType, band, formulaId, page],
  );

  // Any filter change invalidates the current page number.
  const onFilter = (set: (v: string) => void) => (v: string) => { set(v); setPage(1); };

  const rows = scores.data?.items ?? [];

  // Re-score one target against its own formula, reading its metrics live. The
  // request omits `metrics` deliberately — that is what tells the API to gather
  // the target's current numbers rather than score it against a supplied set.
  const [rescoring, setRescoring] = useState<string | null>(null);
  const [rescoreError, setRescoreError] = useState<string | null>(null);
  const refetchScores = scores.refetch;
  const rescore = async (row: HealthScoreRow) => {
    setRescoring(row.id);
    setRescoreError(null);
    try {
      await trustQualityApi.recalculateTarget("health", {
        target_type: row.target_type, target_id: row.target_id, formula_id: row.formula_id });
      refetchScores();
    } catch (e) {
      setRescoreError(e instanceof Error ? e.message : "Could not re-score this target.");
    } finally {
      setRescoring(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 190 }}>
            <Select label="Target type" value={targetType} onChange={onFilter(setTargetType)}
              options={[{ value: "", label: "All target types" },
                ...TQ_ENUMS.healthTargets.map(v => ({ value: v, label: v.replace(/_/g, " ") }))]} />
          </div>
          <div style={{ minWidth: 190 }}>
            <Select label="Band" value={band} onChange={onFilter(setBand)}
              options={[{ value: "", label: "All bands" },
                { value: "__unbanded__", label: "Unbanded (insufficient data)" },
                ...Object.keys(BAND_TONE).map(v => ({ value: v, label: v.replace(/_/g, " ") }))]} />
          </div>
          <div style={{ minWidth: 220 }}>
            <Select label="Formula" value={formulaId} onChange={onFilter(setFormulaId)}
              options={[{ value: "", label: "All formulas" },
                ...formulas.map(f => ({ value: f.id, label: f.name }))]} />
          </div>
          <Btn size="sm" variant="ghost" onClick={() => scores.refetch()}>Refresh</Btn>
        </div>
        {rescoreError && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "10px 0 0" }}>{rescoreError}</p>
        )}
      </Card>

      <Card padding={0}>
        {scores.loading ? <Spinner /> : rows.length === 0 ? (
          <EmptyState icon={<Gauge />} title="No health scores yet"
            description="Run a recalculation to score targets against the active formulas, or adjust the filters above." />
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 16px" }}>Target</th>
                  <th style={{ padding: "10px 16px" }}>Formula</th>
                  <th style={{ padding: "10px 16px", width: 160 }}>Score</th>
                  <th style={{ padding: "10px 16px" }}>Band</th>
                  <th style={{ padding: "10px 16px" }}>Calculated</th>
                  <th style={{ padding: "10px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {rows.map(s => (
                    <React.Fragment key={s.id}>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 16px" }}>
                          <div style={{ fontWeight: 600 }}>
                            {/* A score can outlive its target (the tenant was deleted). Say
                                so rather than rendering a blank cell that looks like a bug. */}
                            {s.target_name ?? <span style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>
                              Deleted target
                            </span>}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                            {s.target_type.replace(/_/g, " ")} · {s.target_id.slice(0, 8)}
                          </div>
                        </td>
                        <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{s.formula_name ?? "—"}</td>
                        <td style={{ padding: "10px 16px" }}><ScoreBar score={s.score} /></td>
                        <td style={{ padding: "10px 16px" }}>
                          {s.band_key
                            ? <Badge variant={BAND_TONE[s.band_key] ?? "muted"}>{s.band_key.replace(/_/g, " ")}</Badge>
                            : <span title="Too few of the formula's metrics were measurable to band this target">
                                <Badge variant="muted">unbanded</Badge>
                              </span>}
                        </td>
                        <td style={{ padding: "10px 16px", color: "var(--text-tertiary)", fontSize: 12 }}>
                          {String(s.calculated_at ?? "").replace("T", " ").slice(0, 16) || "—"}
                        </td>
                        <td style={{ padding: "10px 16px", whiteSpace: "nowrap" }}>
                          <Btn size="sm" variant="ghost"
                            onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                            {expanded === s.id ? "Hide" : "Why?"}
                          </Btn>
                          {/* Re-score just this target from its live metrics. Without
                              it the only way to refresh one provider was a whole
                              platform sweep. */}
                          <Btn size="sm" variant="ghost" disabled={rescoring === s.id}
                            onClick={() => rescore(s)}>
                            {rescoring === s.id ? "…" : "Rescore"}
                          </Btn>
                        </td>
                      </tr>
                      {expanded === s.id && (
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          <td colSpan={6} style={{ padding: 0, background: "var(--surface-sunken)" }}>
                            <Breakdown row={s} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} total={scores.data?.total ?? 0}
              pageSize={PAGE_SIZE} onPage={setPage} alwaysShow />
          </>
        )}
      </Card>
    </div>
  );
}

/** A score with the band colour it earned, so the table scans at a glance. */
function ScoreBar({ score }: { score: number }) {
  const tone = score >= 80 ? "var(--success)" : score >= 60 ? "var(--info)"
    : score >= 40 ? "var(--warning)" : "var(--danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 999, overflow: "hidden", minWidth: 60 }}>
        <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, score))}%`,
          background: tone, borderRadius: 999 }} />
      </div>
      <span style={{ fontWeight: 700, fontSize: 13, minWidth: 38, textAlign: "right" }}>{score.toFixed(1)}</span>
    </div>
  );
}

/** Why the target scored what it scored — the stored component breakdown. */
function Breakdown({ row }: { row: HealthScoreRow }) {
  const comps = row.component_breakdown ?? [];
  const pens = row.penalties ?? [];
  const bons = row.bonuses ?? [];
  const actions = row.recommended_actions ?? [];
  return (
    <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
      {row.band_key === null && (
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 12,
          color: "var(--warning-text)", background: "var(--warning-bg)", padding: "8px 10px",
          borderRadius: "var(--radius-md)", border: "1px solid var(--warning-border)" }}>
          <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            Not enough of this formula was measurable to assign a band, so no band was given
            rather than one this target has not earned. Bands gate commission and bookability.
          </span>
        </div>
      )}
      {comps.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
            letterSpacing: "0.05em", color: "var(--text-tertiary)", marginBottom: 6 }}>Components</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead><tr style={{ textAlign: "left", color: "var(--text-tertiary)" }}>
              <th style={{ padding: "4px 8px 4px 0" }}>Metric</th>
              <th style={{ padding: "4px 8px" }}>Raw</th>
              <th style={{ padding: "4px 8px" }}>Normalised</th>
              <th style={{ padding: "4px 8px" }}>Weight</th>
              <th style={{ padding: "4px 8px" }}>Contribution</th>
            </tr></thead>
            <tbody>
              {comps.map((c, i) => (
                <tr key={`${c.metric_key}-${i}`}>
                  <td style={{ padding: "4px 8px 4px 0", fontFamily: "monospace" }}>{c.metric_key}</td>
                  <td style={{ padding: "4px 8px" }}>{String(c.raw_value ?? "—")}</td>
                  <td style={{ padding: "4px 8px" }}>{c.normalized?.toFixed(1)}</td>
                  <td style={{ padding: "4px 8px" }}>{c.weight_percent}%</td>
                  <td style={{ padding: "4px 8px", fontWeight: 600 }}>{c.contribution?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", fontSize: 12 }}>
        {pens.length > 0 && (
          <div>
            <span style={{ color: "var(--danger-text)", fontWeight: 700 }}>Penalties: </span>
            {pens.map(p => `${p.metric_key} −${p.penalty_points}`).join(", ")}
          </div>
        )}
        {bons.length > 0 && (
          <div>
            <span style={{ color: "var(--success-text)", fontWeight: 700 }}>Bonuses: </span>
            {bons.map(b => `${b.metric_key} +${b.bonus_points}`).join(", ")}
          </div>
        )}
      </div>
      {actions.length > 0 && (
        <div style={{ fontSize: 12 }}>
          <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>Recommended: </span>
          {actions.join("; ")}
        </div>
      )}
      {comps.length === 0 && pens.length === 0 && bons.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          No breakdown was stored for this score — re-run a recalculation to populate it.
        </p>
      )}
    </div>
  );
}
