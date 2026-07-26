"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { recommendationApi, RecommendationRule, SimulateResult } from "../../../../../lib/api";

const RULE_TYPES = [
  "brand", "service_option", "issue_type", "document_requirement",
  "checklist_template", "pricing_template", "commission_template",
  "workflow_template", "provider_default", "customer_next_step",
];
const SCOPES = ["platform", "vertical", "category", "service", "tenant", "location", "customer_flow"];
const STATUS_COLORS: Record<string, string> = {
  active: "#dcfce7", draft: "#f3f4f6", inactive: "#fef9c3", archived: "#fef2f2",
};

export default function RecommendationRuleDetailPage() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const [rule, setRule] = useState<RecommendationRule | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveOk, setSaveOk] = useState(false);

  // Edit form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [ruleType, setRuleType] = useState("brand");
  const [scope, setScope] = useState("platform");
  const [verticalType, setVerticalType] = useState("");
  const [priority, setPriority] = useState("100");
  const [conditionJson, setConditionJson] = useState("{}");
  const [recommendationJson, setRecommendationJson] = useState("{}");
  const [explanationTemplate, setExplanationTemplate] = useState("");

  // Simulate
  const [simContext, setSimContext] = useState('{"context_type": "admin_bulk_setup", "vertical_type": "home_services"}');
  const [simResult, setSimResult] = useState<SimulateResult | null>(null);
  const [simRunning, setSimRunning] = useState(false);
  const [simError, setSimError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await recommendationApi.getRule(ruleId);
      setRule(r);
      setName(r.name);
      setDescription(r.description ?? "");
      setRuleType(r.rule_type);
      setScope(r.scope);
      setVerticalType(r.vertical_type ?? "");
      setPriority(String(r.priority));
      setConditionJson(JSON.stringify(r.condition_json ?? {}, null, 2));
      setRecommendationJson(JSON.stringify(r.recommendation_json ?? {}, null, 2));
      setExplanationTemplate(r.explanation_template ?? "");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [ruleId]);

  const handleSave = async () => {
    setSaveError(""); setSaveOk(false); setSaving(true);
    try {
      let condition_json: Record<string, unknown> = {};
      let recommendation_json: Record<string, unknown> = {};
      try { condition_json = JSON.parse(conditionJson); } catch { setSaveError("condition_json is not valid JSON"); setSaving(false); return; }
      try { recommendation_json = JSON.parse(recommendationJson); } catch { setSaveError("recommendation_json is not valid JSON"); setSaving(false); return; }
      await recommendationApi.updateRule(ruleId, {
        name, description: description || undefined, rule_type: ruleType,
        scope, vertical_type: verticalType || undefined, priority: Number(priority),
        condition_json, recommendation_json,
        explanation_template: explanationTemplate || undefined,
      });
      setSaveOk(true);
      await load();
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleLifecycle = async (action: "activate" | "deactivate" | "archive") => {
    try {
      if (action === "activate") await recommendationApi.activateRule(ruleId);
      else if (action === "deactivate") await recommendationApi.deactivateRule(ruleId);
      else if (action === "archive") { if (!confirm("Archive this rule?")) return; await recommendationApi.archiveRule(ruleId); }
      await load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Action failed");
    }
  };

  const handleSimulate = async () => {
    setSimError(""); setSimRunning(true); setSimResult(null);
    try {
      let ctx: Record<string, unknown> = {};
      try { ctx = JSON.parse(simContext); } catch { setSimError("Context is not valid JSON"); setSimRunning(false); return; }
      const res = await recommendationApi.simulateRule(ruleId, ctx);
      setSimResult(res);
    } catch (e: unknown) {
      setSimError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setSimRunning(false);
    }
  };

  if (loading) return <div style={{ padding: "2rem" }}>Loading...</div>;
  if (!rule) return <div style={{ padding: "2rem" }}>Rule not found.</div>;

  return (
    <div style={{ padding: "1.5rem", maxWidth: "900px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/admin/automation/recommendation-rules" style={{ color: "#6b7280", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Back to Recommendation Rules
        </Link>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: "0.5rem" }}>
          <div>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, margin: 0 }}>{rule.name}</h1>
            <code style={{ fontSize: "0.75rem", color: "#9ca3af" }}>{rule.code}</code>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem", borderRadius: "9999px", background: STATUS_COLORS[rule.status] ?? "#f3f4f6" }}>
              {rule.status}
            </span>
            {rule.status !== "active" && rule.status !== "archived" && (
              <button onClick={() => handleLifecycle("activate")}
                style={{ fontSize: "0.75rem", background: "var(--success)", color: "#fff", border: "none", padding: "0.3rem 0.7rem", borderRadius: "0.25rem", cursor: "pointer" }}>
                Activate
              </button>
            )}
            {rule.status === "active" && (
              <button onClick={() => handleLifecycle("deactivate")}
                style={{ fontSize: "0.75rem", background: "var(--warning)", color: "#fff", border: "none", padding: "0.3rem 0.7rem", borderRadius: "0.25rem", cursor: "pointer" }}>
                Deactivate
              </button>
            )}
            {rule.status !== "archived" && (
              <button onClick={() => handleLifecycle("archive")}
                style={{ fontSize: "0.75rem", background: "var(--danger)", color: "#fff", border: "none", padding: "0.3rem 0.7rem", borderRadius: "0.25rem", cursor: "pointer" }}>
                Archive
              </button>
            )}
          </div>
        </div>
      </div>

      {saveError && <div style={{ background: "#fef2f2", color: "var(--danger)", padding: "0.5rem 0.75rem", borderRadius: "0.375rem", marginBottom: "1rem", fontSize: "0.85rem" }}>{saveError}</div>}
      {saveOk && <div style={{ background: "#f0fdf4", color: "var(--success)", padding: "0.5rem 0.75rem", borderRadius: "0.375rem", marginBottom: "1rem", fontSize: "0.85rem" }}>Saved successfully</div>}

      {/* Edit form */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem" }}>Rule Definition</h2>

        {[
          { label: "Name", val: name, set: setName },
          { label: "Description", val: description, set: setDescription },
          { label: "Vertical Type", val: verticalType, set: setVerticalType },
          { label: "Priority", val: priority, set: setPriority },
          { label: "Explanation Template", val: explanationTemplate, set: setExplanationTemplate },
        ].map(({ label, val, set }) => (
          <div key={label} style={{ marginBottom: "0.75rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>{label}</label>
            <input value={val} onChange={e => set(e.target.value)}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem", boxSizing: "border-box" }} />
          </div>
        ))}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>Rule Type</label>
            <select value={ruleType} onChange={e => setRuleType(e.target.value)}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem" }}>
              {RULE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>Scope</label>
            <select value={scope} onChange={e => setScope(e.target.value)}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem" }}>
              {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>Condition JSON</label>
          <p style={{ fontSize: "0.7rem", color: "#6b7280", margin: "0 0 0.2rem" }}>
            Allowed keys: vertical_type, category_code, service_codes_any, city_tier_any, requires_brand, requires_schedule, etc.
          </p>
          <textarea value={conditionJson} onChange={e => setConditionJson(e.target.value)} rows={4}
            style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem", fontFamily: "monospace", fontSize: "0.78rem", boxSizing: "border-box" }} />
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>Recommendation JSON</label>
          <p style={{ fontSize: "0.7rem", color: "#6b7280", margin: "0 0 0.2rem" }}>
            Must include entity_type (brand|service_option|issue_type|…) and entity_codes array.
          </p>
          <textarea value={recommendationJson} onChange={e => setRecommendationJson(e.target.value)} rows={4}
            style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem", fontFamily: "monospace", fontSize: "0.78rem", boxSizing: "border-box" }} />
        </div>

        <button onClick={handleSave} disabled={saving}
          style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {/* Simulate */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" }}>Simulate Rule</h2>
        <p style={{ fontSize: "0.8rem", color: "#6b7280", marginBottom: "0.75rem" }}>
          Test this rule against a context without mutating the database.
        </p>
        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.2rem" }}>Simulation Context (JSON)</label>
          <textarea value={simContext} onChange={e => setSimContext(e.target.value)} rows={3}
            style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.45rem 0.75rem", fontFamily: "monospace", fontSize: "0.78rem", boxSizing: "border-box" }} />
        </div>
        {simError && <div style={{ background: "#fef2f2", color: "var(--danger)", padding: "0.4rem 0.75rem", borderRadius: "0.375rem", marginBottom: "0.5rem", fontSize: "0.8rem" }}>{simError}</div>}
        <button onClick={handleSimulate} disabled={simRunning}
          style={{ background: "#4f46e5", color: "#fff", border: "none", padding: "0.5rem 1.25rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: simRunning ? 0.6 : 1 }}>
          {simRunning ? "Simulating..." : "Run Simulation"}
        </button>

        {simResult && (
          <div style={{ marginTop: "1.25rem" }}>
            <div style={{ display: "flex", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <div style={{ background: simResult.data.matched ? "#dcfce7" : "#fef2f2", border: `1px solid ${simResult.data.matched ? "#bbf7d0" : "#fecaca"}`, borderRadius: "0.375rem", padding: "0.5rem 1rem" }}>
                <span style={{ fontWeight: 700, color: simResult.data.matched ? "var(--success)" : "var(--danger)" }}>
                  {simResult.data.matched ? "✓ Matched" : "✗ Not Matched"}
                </span>
              </div>
            </div>

            {simResult.data.recommendations.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                  Recommendations ({simResult.data.recommendations.length})
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#f9fafb" }}>
                      {["Type", "Name", "Confidence", "Explanation"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "0.4rem 0.6rem", fontSize: "0.7rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {simResult.data.recommendations.map((rec, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.75rem", fontFamily: "monospace" }}>{rec.entity_type}</td>
                        <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.8rem", fontWeight: 600 }}>{rec.name}</td>
                        <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.75rem" }}>{rec.confidence_score?.toFixed(2) ?? "—"}</td>
                        <td style={{ padding: "0.4rem 0.6rem", fontSize: "0.75rem", color: "#4b5563" }}>{rec.explanation ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {simResult.data.warnings.length > 0 && (
              <div style={{ marginTop: "0.75rem" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "0.25rem", color: "var(--warning)" }}>Warnings</div>
                <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                  {simResult.data.warnings.map((w, i) => (
                    <li key={i} style={{ fontSize: "0.78rem", color: "#92400e", marginBottom: "0.2rem" }}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <p style={{ fontSize: "0.7rem", color: "#9ca3af", marginTop: "0.75rem", fontStyle: "italic" }}>{simResult.data.note}</p>
          </div>
        )}
      </div>
    </div>
  );
}
