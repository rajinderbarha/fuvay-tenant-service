"use client";

import { useEffect, useState } from "react";
import { recommendationApi, RecommendationRule } from "../../../../lib/api";

const RULE_TYPES = [
  "brand", "service_option", "issue_type", "document_requirement",
  "checklist_template", "pricing_template", "commission_template",
  "workflow_template", "provider_default", "customer_next_step",
];
const SCOPES = ["platform", "vertical", "category", "service", "tenant", "location", "customer_flow"];
const STATUS_COLORS: Record<string, string> = {
  active:   "#dcfce7",
  draft:    "#f3f4f6",
  inactive: "#fef9c3",
  archived: "#fef2f2",
};

export default function RecommendationRulesPage() {
  const [rules, setRules] = useState<RecommendationRule[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    code: "", name: "", description: "", rule_type: "brand",
    scope: "platform", vertical_type: "", priority: "100", status: "draft",
    condition_json: "{}", recommendation_json: "{}",
    explanation_template: "",
  });
  const [formError, setFormError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await recommendationApi.listRules({
        status: statusFilter || undefined,
        rule_type: typeFilter || undefined,
        page_size: 50,
      });
      setRules(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [statusFilter, typeFilter]);

  const handleCreate = async () => {
    setFormError("");
    setCreating(true);
    try {
      let condition_json: Record<string, unknown> = {};
      let recommendation_json: Record<string, unknown> = {};
      try { condition_json = JSON.parse(form.condition_json); } catch { setFormError("condition_json is not valid JSON"); setCreating(false); return; }
      try { recommendation_json = JSON.parse(form.recommendation_json); } catch { setFormError("recommendation_json is not valid JSON"); setCreating(false); return; }
      await recommendationApi.createRule({
        code: form.code,
        name: form.name,
        description: form.description || undefined,
        rule_type: form.rule_type,
        scope: form.scope,
        vertical_type: form.vertical_type || undefined,
        priority: Number(form.priority),
        condition_json,
        recommendation_json,
        explanation_template: form.explanation_template || undefined,
      });
      setShowCreate(false);
      setForm({ code: "", name: "", description: "", rule_type: "brand", scope: "platform",
                vertical_type: "", priority: "100", status: "draft", condition_json: "{}", recommendation_json: "{}", explanation_template: "" });
      await load();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (id: string) => {
    await recommendationApi.activateRule(id);
    await load();
  };

  const handleDeactivate = async (id: string) => {
    await recommendationApi.deactivateRule(id);
    await load();
  };

  const handleArchive = async (id: string) => {
    if (!confirm("Archive this rule?")) return;
    await recommendationApi.archiveRule(id);
    await load();
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>Recommendation Rules</h1>
          <p style={{ color: "#6b7280", margin: "0.25rem 0 0" }}>
            Define automatic recommendation rules for brands, options, issues, documents, and more
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <a href="/admin/automation/recommendation-results"
            style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", color: "#4b5563", textDecoration: "none", fontSize: "0.875rem" }}>
            View Results
          </a>
          <button onClick={() => setShowCreate(true)}
            style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.2rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600 }}>
            + New Rule
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Statuses</option>
          {["draft", "active", "inactive", "archived"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          style={{ border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.4rem 0.75rem" }}>
          <option value="">All Types</option>
          {RULE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <span style={{ fontSize: "0.85rem", color: "#6b7280", alignSelf: "center" }}>{total} total</span>
      </div>

      {/* Table */}
      {loading ? (
        <p style={{ color: "#6b7280" }}>Loading...</p>
      ) : rules.length === 0 ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "#9ca3af" }}>
          <p>No recommendation rules yet.</p>
          <button onClick={() => setShowCreate(true)}
            style={{ marginTop: "1rem", background: "#1e3a5f", color: "#fff", border: "none", padding: "0.6rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600 }}>
            Create First Rule
          </button>
        </div>
      ) : (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "0.5rem", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Name / Code", "Type", "Scope", "Priority", "Status", "Updated", "Actions"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{rule.name}</div>
                    <div style={{ fontSize: "0.7rem", color: "#9ca3af", fontFamily: "monospace" }}>{rule.code}</div>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>{rule.rule_type}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>
                    {rule.scope}
                    {rule.vertical_type && <span style={{ color: "#6b7280" }}> / {rule.vertical_type}</span>}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.78rem" }}>{rule.priority}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", borderRadius: "9999px", background: STATUS_COLORS[rule.status] ?? "#f3f4f6" }}>
                      {rule.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", color: "#6b7280" }}>
                    {rule.updated_at ? new Date(rule.updated_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                      <a href={`/admin/automation/recommendation-rules/${rule.id}`}
                        style={{ fontSize: "0.72rem", color: "#1e3a5f", textDecoration: "none" }}>Edit</a>
                      {rule.status !== "active" && rule.status !== "archived" && (
                        <button onClick={() => handleActivate(rule.id)}
                          style={{ fontSize: "0.72rem", color: "var(--success)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>Activate</button>
                      )}
                      {rule.status === "active" && (
                        <button onClick={() => handleDeactivate(rule.id)}
                          style={{ fontSize: "0.72rem", color: "var(--warning)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>Deactivate</button>
                      )}
                      {rule.status !== "archived" && (
                        <button onClick={() => handleArchive(rule.id)}
                          style={{ fontSize: "0.72rem", color: "var(--danger)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>Archive</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#fff", borderRadius: "0.75rem", padding: "2rem", width: "600px", maxHeight: "90vh", overflowY: "auto" }}>
            <h2 style={{ margin: "0 0 1.25rem", fontWeight: 700 }}>Create Recommendation Rule</h2>
            {formError && <div style={{ background: "#fef2f2", color: "var(--danger)", padding: "0.5rem 0.75rem", borderRadius: "0.375rem", marginBottom: "1rem", fontSize: "0.85rem" }}>{formError}</div>}

            {[
              { label: "Code *", field: "code", placeholder: "ac_brand_recommendations" },
              { label: "Name *", field: "name", placeholder: "Recommend AC Brands for AC Services" },
              { label: "Description", field: "description", placeholder: "Optional description" },
              { label: "Vertical Type", field: "vertical_type", placeholder: "home_services" },
              { label: "Priority", field: "priority", placeholder: "100" },
              { label: "Explanation Template", field: "explanation_template", placeholder: "Recommended because {service_code} uses AC brand defaults." },
            ].map(({ label, field, placeholder }) => (
              <div key={field} style={{ marginBottom: "0.85rem" }}>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>{label}</label>
                <input value={(form as Record<string, string>)[field]} onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                  placeholder={placeholder}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", boxSizing: "border-box" }} />
              </div>
            ))}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.85rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>Rule Type *</label>
                <select value={form.rule_type} onChange={e => setForm(f => ({ ...f, rule_type: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem" }}>
                  {RULE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>Scope *</label>
                <select value={form.scope} onChange={e => setForm(f => ({ ...f, scope: e.target.value }))}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem" }}>
                  {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>

            {[
              { label: "Condition JSON *", field: "condition_json", hint: '{"vertical_type": "home_services", "service_codes_any": ["ac_repair"]}' },
              { label: "Recommendation JSON *", field: "recommendation_json", hint: '{"entity_type": "brand", "entity_codes": ["samsung", "lg"]}' },
            ].map(({ label, field, hint }) => (
              <div key={field} style={{ marginBottom: "0.85rem" }}>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>{label}</label>
                <p style={{ fontSize: "0.7rem", color: "#6b7280", margin: "0 0 0.25rem" }}>Example: <code>{hint}</code></p>
                <textarea value={(form as Record<string, string>)[field]}
                  onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                  rows={3}
                  style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontFamily: "monospace", fontSize: "0.78rem", boxSizing: "border-box" }} />
              </div>
            ))}

            <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
              <button onClick={() => { setShowCreate(false); setFormError(""); }}
                style={{ flex: 1, padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleCreate} disabled={creating}
                style={{ flex: 1, padding: "0.5rem", background: "#1e3a5f", color: "#fff", border: "none", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: creating ? 0.6 : 1 }}>
                {creating ? "Creating..." : "Create Rule"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
