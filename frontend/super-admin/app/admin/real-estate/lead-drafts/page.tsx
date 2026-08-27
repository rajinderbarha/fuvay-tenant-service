"use client";
import { TableSurface } from "@serviceos/design-system";

import React, { useEffect, useState, useCallback } from "react";
import {
  adminRealEstateLeadApi,
  RealEstateLeadDraft,
  RealEstateLeadDraftEvent,
  RealEstateLeadRoutingRule,
} from "@/lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  draft:                   { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  collecting_details:      { background: "var(--info-bg)",        color: "var(--info-text)" },
  location_checked:        { background: "var(--info-bg)",        color: "var(--info-text)" },
  providers_found:         { background: "var(--success-bg)",     color: "var(--success-text)" },
  no_provider_exact_match: { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  fallback_available:      { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  ready_for_confirmation:  { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  confirmed:               { background: "var(--success-bg)",     color: "var(--success-text)" },
  expired:                 { background: "var(--danger-bg)",      color: "var(--danger-text)" },
  cancelled:               { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  failed:                  { background: "var(--danger-bg)",      color: "var(--danger-text)" },
};

const SCORE_COLOR: Record<string, string> = {
  cold: "var(--info-text)",
  warm: "var(--warning-text)",
  hot:  "var(--danger-text)",
};

const INTENT_LABELS: Record<string, string> = {
  buy: "Buy Property", rent: "Rent Property", sell: "Sell Property",
  site_visit: "Site Visit", consultation: "Consultation",
  commercial: "Commercial", plot: "Plot", unknown: "Unknown",
};

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const btnStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius:"var(--radius-md)", cursor: "pointer", fontFamily: "inherit",
  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
};

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

const inputStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
      ...(STATUS_STYLE[status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function formatCurrency(val: number | null) {
  if (val === null || val === undefined) return "—";
  if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
  if (val >= 100000)   return `₹${(val / 100000).toFixed(1)}L`;
  return `₹${val.toLocaleString("en-IN")}`;
}

function DraftDetailModal({ draft, onClose }: { draft: RealEstateLeadDraft; onClose: () => void }) {
  const [events, setEvents] = useState<RealEstateLeadDraftEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);

  useEffect(() => {
    adminRealEstateLeadApi.getDraftEvents(draft.id)
      .then((r) => setEvents(r.events ?? []))
      .catch(() => setEvents([]))
      .finally(() => setLoadingEvents(false));
  }, [draft.id]);

  const score = draft.lead_score_snapshot as Record<string, unknown> | null;
  const summary = draft.lead_summary as Record<string, unknown> | null;
  const fallback = draft.fallback_payload as Record<string, unknown> | null;
  const scoreLabel = score?.score_label as string | undefined;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 50, padding: 16 }}>
      <div style={{ background: "var(--surface)", borderRadius:"var(--radius-xl, 1rem)", boxShadow: "0 16px 48px rgba(0,0,0,0.22)",
        maxWidth: 720, width: "100%", maxHeight: "90vh", overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "20px 24px", borderBottom: "1px solid var(--border)", position: "sticky", top: 0,
          background: "var(--surface)", zIndex: 1 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Lead Draft</h2>
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{draft.id}</p>
          </div>
          <button onClick={onClose} style={{ fontSize: 22, background: "none", border: "none", cursor: "pointer",
            color: "var(--text-tertiary)", lineHeight: 1 }}>×</button>
        </div>

        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>Status</p>
              <StatusBadge status={draft.status} />
            </div>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>Intent</p>
              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
                {INTENT_LABELS[draft.lead_intent ?? ""] ?? draft.lead_intent ?? "—"}
              </span>
            </div>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>Property Type</p>
              <span style={{ fontSize: 13, color: "var(--text-primary)", textTransform: "capitalize" }}>
                {draft.property_type ?? "—"}
              </span>
            </div>
            <div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 6px" }}>Lead Score</p>
              {score ? (
                <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase",
                  color: SCORE_COLOR[scoreLabel ?? ""] ?? "var(--text-primary)" }}>
                  {scoreLabel} ({score.score as number})
                </span>
              ) : (
                <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Not calculated</span>
              )}
            </div>
          </div>

          <div style={{ background: "var(--surface-sunken)", borderRadius: 10, padding: 16 }}>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Location</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, fontSize: 13 }}>
              <div><span style={{ color: "var(--text-tertiary)" }}>City </span>{draft.city ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Locality </span>{draft.locality ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Pincode </span>{draft.zipcode ?? "—"}</div>
            </div>
          </div>

          <div style={{ background: "var(--surface-sunken)", borderRadius: 10, padding: 16 }}>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Budget / Rent</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
              <div>
                <span style={{ color: "var(--text-tertiary)" }}>Buy Budget </span>
                {draft.budget_min !== null || draft.budget_max !== null
                  ? `${formatCurrency(draft.budget_min)} – ${formatCurrency(draft.budget_max)}`
                  : "—"}
              </div>
              <div>
                <span style={{ color: "var(--text-tertiary)" }}>Rent Range </span>
                {draft.rent_min !== null || draft.rent_max !== null
                  ? `${formatCurrency(draft.rent_min)} – ${formatCurrency(draft.rent_max)}/mo`
                  : "—"}
              </div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Bedrooms </span>{draft.bedrooms ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Furnishing </span>{draft.furnishing ?? "—"}</div>
            </div>
          </div>

          <div style={{ background: "var(--surface-sunken)", borderRadius: 10, padding: 16 }}>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Customer</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
              <div><span style={{ color: "var(--text-tertiary)" }}>Name </span>{draft.customer_name ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Phone </span>{draft.customer_phone ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Email </span>{draft.customer_email ?? "—"}</div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Contact Time </span>{draft.preferred_contact_time ?? "—"}</div>
            </div>
            {draft.notes && (
              <p style={{ marginTop: 8, fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>{draft.notes}</p>
            )}
          </div>

          {draft.provider_options && Array.isArray(draft.provider_options) && draft.provider_options.length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Provider Options</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {(draft.provider_options as Record<string, unknown>[]).map((p, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: "8px 14px", fontSize: 13 }}>
                    <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>{p.business_name as string ?? "Provider"}</span>
                    <span style={{ color: "var(--text-tertiary)" }}>{p.city as string} · {p.match_reason as string}</span>
                    {p.rating !== null && p.rating !== undefined && (
                      <span style={{ color: "var(--warning-text)" }}>★ {p.rating as number}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {fallback && (
            <div style={{ background: "var(--warning-bg)", border: "1px solid var(--border)", borderRadius: 10, padding: 14 }}>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--warning-text)", margin: "0 0 6px" }}>Fallback Payload</p>
              <p style={{ fontSize: 13, color: "var(--warning-text)", margin: "0 0 4px" }}>{fallback.message as string}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>Type: {fallback.fallback_type as string}</p>
            </div>
          )}

          {summary && (
            <details style={{ background: "var(--surface-sunken)", borderRadius: 10, padding: 14 }}>
              <summary style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", cursor: "pointer" }}>
                Lead Summary JSON
              </summary>
              <pre style={{ marginTop: 8, fontSize: 11, color: "var(--text-secondary)", overflowX: "auto", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(summary, null, 2)}
              </pre>
            </details>
          )}

          <div>
            <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Event Log</p>
            {loadingEvents ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading events…</p>
            ) : events.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No events recorded.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {events.map((evt) => (
                  <div key={evt.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 11,
                    borderLeft: "2px solid var(--info-border, var(--border))", paddingLeft: 10, paddingTop: 2, paddingBottom: 2 }}>
                    <span style={{ color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                      {new Date(evt.created_at).toLocaleTimeString()}
                    </span>
                    <span style={{ padding: "1px 6px", borderRadius: 4, background: "var(--info-bg)",
                      color: "var(--info-text)", fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
                      {evt.event_type}
                    </span>
                    <span style={{ color: "var(--text-tertiary)" }}>{evt.actor_type}</span>
                    {evt.message && <span style={{ color: "var(--text-secondary)" }}>{evt.message}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function RoutingRulesTab() {
  const [rules, setRules]     = useState<RealEstateLeadRoutingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newRule, setNewRule] = useState<Partial<RealEstateLeadRoutingRule>>({
    rule_key: "", rule_name: "", match_scope: "city", priority: 0,
    require_provider_bookable: true, require_subscription_active: true,
    require_agent_available: false, require_lead_credit: false,
    max_providers: 5, is_active: true,
  });
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    adminRealEstateLeadApi.listRoutingRules({ active_only: false })
      .then((r) => setRules(r.rules ?? []))
      .catch(() => setRules([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (rule: RealEstateLeadRoutingRule) => {
    try {
      if (rule.is_active) await adminRealEstateLeadApi.deactivateRule(rule.id);
      else await adminRealEstateLeadApi.activateRule(rule.id);
      load();
    } catch {}
  };

  const handleCreate = async () => {
    setSaving(true);
    try { await adminRealEstateLeadApi.createRoutingRule(newRule); setShowAdd(false); load(); }
    catch {} finally { setSaving(false); }
  };

  const labelSt: React.CSSProperties = { fontSize: 11, color: "var(--text-tertiary)", display: "block", marginBottom: 4 };
  const fieldSt: React.CSSProperties = { ...inputStyle, width: "100%", boxSizing: "border-box" };
  const selFSt: React.CSSProperties = { ...selStyle, width: "100%", boxSizing: "border-box" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          {rules.length} routing rule{rules.length !== 1 ? "s" : ""}
        </p>
        <button onClick={() => setShowAdd(true)}
          style={{ ...btnStyle, background: "var(--brand)", color: "white", border: "none" }}>
          + Add Rule
        </button>
      </div>

      {loading ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>
      ) : rules.length === 0 ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No routing rules configured.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunken)" }}>
                {["Rule Key","Name","Intent","Match Scope","Priority","Max Providers","Status","Actions"].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-secondary)" }}>
                    {rule.rule_key}
                  </td>
                  <td style={{ padding: "10px 16px", fontWeight: 500, color: "var(--text-primary)" }}>{rule.rule_name}</td>
                  <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{rule.lead_intent ?? "any"}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <span style={{ background: "var(--info-bg)", color: "var(--info-text)",
                      padding: "2px 8px", borderRadius: 6, fontSize: 11 }}>
                      {rule.match_scope}
                    </span>
                  </td>
                  <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{rule.priority}</td>
                  <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{rule.max_providers}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                      background: rule.is_active ? "var(--success-bg)" : "var(--surface-sunken)",
                      color: rule.is_active ? "var(--success-text)" : "var(--text-tertiary)" }}>
                      {rule.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={{ padding: "10px 16px" }}>
                    <button onClick={() => handleToggle(rule)} style={{
                      fontSize: 12, padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit", border: "none",
                      background: rule.is_active ? "var(--danger-bg)" : "var(--success-bg)",
                      color: rule.is_active ? "var(--danger-text)" : "var(--success-text)",
                    }}>
                      {rule.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        </div>
      )}

      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 50, padding: 16 }}>
          <div style={{ background: "var(--surface)", borderRadius:"var(--radius-xl, 1rem)", padding: 24, maxWidth: 560, width: "100%",
            display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.22)" }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>Add Routing Rule</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={labelSt}>Rule Key *</label>
                <input style={fieldSt} value={newRule.rule_key ?? ""}
                  onChange={e => setNewRule(p => ({ ...p, rule_key: e.target.value }))}
                  placeholder="city_buy_default" />
              </div>
              <div>
                <label style={labelSt}>Rule Name *</label>
                <input style={fieldSt} value={newRule.rule_name ?? ""}
                  onChange={e => setNewRule(p => ({ ...p, rule_name: e.target.value }))}
                  placeholder="City-level buy routing" />
              </div>
              <div>
                <label style={labelSt}>Match Scope</label>
                <select style={selFSt} value={newRule.match_scope ?? "city"}
                  onChange={e => setNewRule(p => ({ ...p, match_scope: e.target.value }))}>
                  {["exact_zipcode","locality","city","district","zone","fallback_city"].map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelSt}>Lead Intent</label>
                <select style={selFSt} value={newRule.lead_intent ?? ""}
                  onChange={e => setNewRule(p => ({ ...p, lead_intent: e.target.value || undefined }))}>
                  <option value="">Any</option>
                  {["buy","rent","sell","site_visit","commercial"].map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelSt}>Priority</label>
                <input type="number" style={fieldSt} value={newRule.priority ?? 0}
                  onChange={e => setNewRule(p => ({ ...p, priority: Number(e.target.value) }))} />
              </div>
              <div>
                <label style={labelSt}>Max Providers</label>
                <input type="number" style={fieldSt} value={newRule.max_providers ?? 5}
                  onChange={e => setNewRule(p => ({ ...p, max_providers: Number(e.target.value) }))} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 12, paddingTop: 4 }}>
              <button onClick={handleCreate} disabled={saving}
                style={{ flex: 1, padding: "8px 0", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)", border: "none",
                  cursor: "pointer", fontFamily: "inherit", background: "var(--brand)", color: "white",
                  opacity: saving ? 0.5 : 1 }}>
                {saving ? "Saving…" : "Create Rule"}
              </button>
              <button onClick={() => setShowAdd(false)}
                style={{ flex: 1, padding: "8px 0", fontSize: 13, borderRadius:"var(--radius-md)",
                  border: "1px solid var(--border)", cursor: "pointer", fontFamily: "inherit",
                  background: "var(--surface)", color: "var(--text-secondary)" }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RealEstateLeadDraftsPage() {
  const [tab, setTab]             = useState<"drafts" | "rules">("drafts");
  const [drafts, setDrafts]       = useState<RealEstateLeadDraft[]>([]);
  const [total, setTotal]         = useState(0);
  const [loading, setLoading]     = useState(true);
  const [selectedDraft, setSelectedDraft] = useState<RealEstateLeadDraft | null>(null);

  const [statusFilter, setStatusFilter] = useState("");
  const [cityFilter, setCityFilter]     = useState("");
  const [intentFilter, setIntentFilter] = useState("");
  const [offset, setOffset]             = useState(0);
  const limit = 50;

  const loadDrafts = useCallback(() => {
    setLoading(true);
    adminRealEstateLeadApi.listDrafts({
      status: statusFilter || undefined,
      city:   cityFilter   || undefined,
      intent: intentFilter || undefined,
      limit, offset,
    }).then((r) => {
      setDrafts(r.drafts ?? []);
      setTotal(r.total ?? 0);
    }).catch(() => setDrafts([]))
    .finally(() => setLoading(false));
  }, [statusFilter, cityFilter, intentFilter, offset]);

  useEffect(() => { if (tab === "drafts") loadDrafts(); }, [tab, loadDrafts]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 1400, margin: "0 auto" }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          Real Estate Lead Drafts
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Sprint 18 — Real estate chatbot lead capture flow. Read-only view of customer inquiries.
        </p>
      </div>

      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)" }}>
        {(["drafts", "rules"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 16px", fontSize: 13, fontWeight: 500, border: "none", background: "none",
            cursor: "pointer", fontFamily: "inherit",
            borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
            color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", marginBottom: -1,
          }}>
            {t === "drafts" ? "Lead Drafts" : "Routing Rules"}
          </button>
        ))}
      </div>

      {tab === "drafts" && (
        <>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setOffset(0); }} style={selStyle}>
              <option value="">All Statuses</option>
              {["draft","collecting_details","location_checked","providers_found","no_provider_exact_match",
                "fallback_available","ready_for_confirmation","confirmed","expired","cancelled","failed"].map(s => (
                <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
              ))}
            </select>
            <input value={cityFilter} onChange={e => { setCityFilter(e.target.value); setOffset(0); }}
              placeholder="Filter by city…" style={{ ...inputStyle, width: 160 }} />
            <select value={intentFilter} onChange={e => { setIntentFilter(e.target.value); setOffset(0); }} style={selStyle}>
              <option value="">All Intents</option>
              {["buy","rent","sell","site_visit","consultation","commercial","plot"].map(i => (
                <option key={i} value={i}>{i.replace(/_/g, " ")}</option>
              ))}
            </select>
            <button onClick={loadDrafts}
              style={{ ...btnStyle, background: "var(--brand)", color: "white", border: "none" }}>
              Refresh
            </button>
          </div>

          {loading ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>
          ) : drafts.length === 0 ? (
            <div style={{ textAlign: "center", padding: "64px 0", color: "var(--text-tertiary)" }}>
              <p style={{ fontSize: 16, margin: "0 0 4px" }}>No lead drafts found</p>
              <p style={{ fontSize: 13, margin: 0 }}>Lead drafts appear here when customers start the real estate chatbot flow.</p>
            </div>
          ) : (
            <>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                {total} total · showing {drafts.length}
              </p>
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
                <div style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)" }}>
                        {["Draft ID","Intent","Property Type","Location","Budget / Rent","Customer","Score","Status","Fallback","Created","Actions"].map(h => (
                          <th key={h} style={th}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {drafts.map((d) => {
                        const score = d.lead_score_snapshot as Record<string, unknown> | null;
                        const scoreLabel = score?.score_label as string | undefined;
                        return (
                          <tr key={d.id} style={{ borderBottom: "1px solid var(--border)" }}>
                            <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                              {d.id.slice(0, 8)}…
                            </td>
                            <td style={{ padding: "10px 16px", textTransform: "capitalize", color: "var(--text-secondary)" }}>
                              {INTENT_LABELS[d.lead_intent ?? ""] ?? d.lead_intent ?? "—"}
                            </td>
                            <td style={{ padding: "10px 16px", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                              {d.property_type ?? "—"}
                            </td>
                            <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                              {d.locality ? `${d.locality}, ` : ""}{d.city ?? "—"}
                            </td>
                            <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                              {d.budget_min !== null || d.budget_max !== null
                                ? `${formatCurrency(d.budget_min)}–${formatCurrency(d.budget_max)}`
                                : d.rent_min !== null || d.rent_max !== null
                                ? `${formatCurrency(d.rent_min)}–${formatCurrency(d.rent_max)}/mo`
                                : "—"}
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              <div style={{ color: "var(--text-primary)", fontSize: 13 }}>{d.customer_name ?? "—"}</div>
                              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{d.customer_phone ?? ""}</div>
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              {scoreLabel ? (
                                <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                                  color: SCORE_COLOR[scoreLabel] ?? "var(--text-primary)" }}>
                                  {scoreLabel}
                                </span>
                              ) : "—"}
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              <StatusBadge status={d.status} />
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              {d.fallback_payload ? (
                                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6,
                                  background: "var(--warning-bg)", color: "var(--warning-text)" }}>
                                  Fallback
                                </span>
                              ) : "—"}
                            </td>
                            <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                              {new Date(d.created_at).toLocaleDateString()}
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              <button onClick={() => setSelectedDraft(d)}
                                style={{ fontSize: 12, color: "var(--accent)", background: "none", border: "none",
                                  cursor: "pointer", padding: 0, textDecoration: "underline" }}>
                                View
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </TableSurface>
                </div>
              </div>

              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}
                  style={{ ...btnStyle, opacity: offset === 0 ? 0.4 : 1, cursor: offset === 0 ? "not-allowed" : "pointer" }}>
                  ← Prev
                </button>
                <button disabled={drafts.length < limit} onClick={() => setOffset(offset + limit)}
                  style={{ ...btnStyle, opacity: drafts.length < limit ? 0.4 : 1, cursor: drafts.length < limit ? "not-allowed" : "pointer" }}>
                  Next →
                </button>
              </div>
            </>
          )}
        </>
      )}

      {tab === "rules" && <RoutingRulesTab />}

      {selectedDraft && (
        <DraftDetailModal draft={selectedDraft} onClose={() => setSelectedDraft(null)} />
      )}
    </div>
  );
}
