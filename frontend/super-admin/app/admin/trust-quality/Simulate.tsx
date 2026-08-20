"use client";
/**
 * Dry-run a badge rule or health formula before activating it.
 *
 * Both simulate endpoints existed on the backend, and `simulateBadgeRule` /
 * `simulateHealthFormula` sat in the API client — with no caller anywhere. So an
 * admin activated a rule that gates commission and customer-visible trust
 * without ever being able to check what it would do first. These panels are the
 * callers.
 *
 * The metric inputs are derived from the rule's own criteria/components, so the
 * admin is only ever asked for values the rule actually reads.
 */
import React, { useState } from "react";
import { CheckCircle2, XCircle, FlaskConical } from "lucide-react";
import { Btn, Badge, Input } from "../../../components/shared/ui";
import {
  trustQualityApi, BadgeSimulationResult, HealthSimulationResult, SimulatedCriterion,
} from "../../../lib/api";
import { useAction } from "../../../hooks/useApi";

/** Numeric-looking values go to the API as numbers; the engine compares numerically. */
function coerce(raw: string): unknown {
  const t = raw.trim();
  if (t === "") return undefined;
  if (t === "true") return true;
  if (t === "false") return false;
  const n = Number(t);
  return Number.isNaN(n) ? t : n;
}

function buildMetrics(values: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(values)) {
    const c = coerce(v);
    if (c !== undefined) out[k] = c;
  }
  return out;
}

function Shell({ title, metricKeys, values, setValues, onRun, running, children }: {
  title: string; metricKeys: string[];
  values: Record<string, string>; setValues: (v: Record<string, string>) => void;
  onRun: () => void; running: boolean; children?: React.ReactNode;
}) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)",
      background: "var(--surface-sunken)", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13,
        fontWeight: 700, marginBottom: 8 }}>
        <FlaskConical size={14} /> {title}
      </div>
      {metricKeys.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Add at least one metric above, then save, to try this rule out.
        </p>
      ) : (
        <>
          <div style={{ display: "grid", gap: 8,
            gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
            {metricKeys.map(k => (
              <Input key={k} label={k} value={values[k] ?? ""}
                onChange={v => setValues({ ...values, [k]: v })} placeholder="value" />
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
            <Btn size="sm" variant="secondary" disabled={running} onClick={onRun}>
              {running ? "Running…" : "Run simulation"}
            </Btn>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              Nothing is saved — this only shows what the rule would decide.
            </span>
          </div>
          {children}
        </>
      )}
    </div>
  );
}

function CriterionRow({ c, passed }: { c: SimulatedCriterion; passed: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, padding: "3px 0" }}>
      {passed
        ? <CheckCircle2 size={13} color="var(--success)" />
        : <XCircle size={13} color="var(--danger)" />}
      <span style={{ fontFamily: "monospace" }}>{c.metric_key}</span>
      <span style={{ color: "var(--text-tertiary)" }}>{c.operator.replace(/_/g, " ")}</span>
      <span style={{ fontWeight: 600 }}>{JSON.stringify(c.expected)}</span>
      <span style={{ color: "var(--text-tertiary)" }}>
        — you entered {c.actual === null || c.actual === undefined ? "nothing" : JSON.stringify(c.actual)}
      </span>
    </div>
  );
}

export function BadgeRuleSimulator({ ruleId, metricKeys }: {
  ruleId: string; metricKeys: string[];
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<BadgeSimulationResult | null>(null);

  const run = useAction(async () => {
    setResult(await trustQualityApi.simulateBadgeRule(ruleId, buildMetrics(values)));
  });

  return (
    <Shell title="Try this rule out" metricKeys={metricKeys} values={values}
      setValues={setValues} onRun={() => run.execute()} running={run.loading}>
      {run.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "8px 0 0" }}>{run.error}</p>}
      {result && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
          <div style={{ marginBottom: 6 }}>
            {result.would_remove_badge
              ? <Badge variant="danger">Badge would be removed</Badge>
              : result.would_award_badge
                ? <Badge variant="success">Badge would be awarded</Badge>
                : <Badge variant="muted">Not eligible — no badge</Badge>}
          </div>
          {result.matched_criteria.map((c, i) => <CriterionRow key={`m${i}`} c={c} passed />)}
          {result.failed_criteria.map((c, i) => <CriterionRow key={`f${i}`} c={c} passed={false} />)}
          {result.removal_matched.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--danger-text)" }}>
                Removal criteria matched
              </div>
              {result.removal_matched.map((c, i) => <CriterionRow key={`r${i}`} c={c} passed />)}
            </div>
          )}
          {result.warnings.map((w, i) => (
            <p key={i} style={{ fontSize: 12, color: "var(--warning-text)", margin: "6px 0 0" }}>{w}</p>
          ))}
        </div>
      )}
    </Shell>
  );
}

export function HealthFormulaSimulator({ formulaId, metricKeys }: {
  formulaId: string; metricKeys: string[];
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<HealthSimulationResult | null>(null);

  const run = useAction(async () => {
    setResult(await trustQualityApi.simulateHealthFormula(formulaId, buildMetrics(values)));
  });

  return (
    <Shell title="Try this formula out" metricKeys={metricKeys} values={values}
      setValues={setValues} onRun={() => run.execute()} running={run.loading}>
      {run.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "8px 0 0" }}>{run.error}</p>}
      {result && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
            <span style={{ fontSize: 24, fontWeight: 800 }}>{result.score.toFixed(1)}</span>
            {result.band_key
              ? <Badge variant="success">{result.band_key.replace(/_/g, " ")}</Badge>
              : <Badge variant="muted">unbanded</Badge>}
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {result.coverage_percent.toFixed(0)}% of the formula was measurable
            </span>
          </div>
          {result.insufficient_data && (
            <p style={{ fontSize: 12, color: "var(--warning-text)", margin: "0 0 8px" }}>
              Too little of the formula could be measured to assign a band. With these
              metrics a real target would be left unbanded rather than given a band it
              has not earned.
            </p>
          )}
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <tbody>
              {result.component_breakdown.map((c, i) => (
                <tr key={i}>
                  <td style={{ padding: "2px 8px 2px 0", fontFamily: "monospace" }}>{c.metric_key}</td>
                  <td style={{ padding: "2px 8px", color: "var(--text-tertiary)" }}>
                    {c.normalized?.toFixed(1)} × {c.weight_percent}%
                  </td>
                  <td style={{ padding: "2px 0", fontWeight: 600, textAlign: "right" }}>
                    +{c.contribution?.toFixed(2)}
                  </td>
                </tr>
              ))}
              {result.penalties_applied.map((p, i) => (
                <tr key={`p${i}`}>
                  <td style={{ padding: "2px 8px 2px 0", fontFamily: "monospace" }}>{p.metric_key}</td>
                  <td style={{ padding: "2px 8px", color: "var(--danger-text)" }}>penalty</td>
                  <td style={{ padding: "2px 0", fontWeight: 600, textAlign: "right", color: "var(--danger-text)" }}>
                    −{p.penalty_points}
                  </td>
                </tr>
              ))}
              {result.bonuses_applied.map((b, i) => (
                <tr key={`b${i}`}>
                  <td style={{ padding: "2px 8px 2px 0", fontFamily: "monospace" }}>{b.metric_key}</td>
                  <td style={{ padding: "2px 8px", color: "var(--success-text)" }}>bonus</td>
                  <td style={{ padding: "2px 0", fontWeight: 600, textAlign: "right", color: "var(--success-text)" }}>
                    +{b.bonus_points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.recommended_actions.length > 0 && (
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "8px 0 0" }}>
              Recommended: {result.recommended_actions.join("; ")}
            </p>
          )}
        </div>
      )}
    </Shell>
  );
}
