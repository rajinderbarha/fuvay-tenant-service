"use client";
/**
 * MODULE-L5-12 — Trust & Quality (badges, provider health, recalculation).
 *
 * The trust_quality engine was registered and live — provider badges, badge
 * award rules, health-score formulas and recalculation jobs, all with real
 * seeded config — but had NO admin UI at all. This is its management console.
 *
 * The admin configures the engine here: creating badge definitions, badge award
 * rules (with metric criteria), and health-score formulas (with weighted
 * components and score bands), then activating/deactivating and recalculating.
 */
import React, { useCallback, useMemo, useState } from "react";
import {
  Award, Star, Shield, ShieldCheck, Crown, Trophy, Medal, Gem, Sparkles,
  BadgeCheck, Flame, Zap, Heart, ThumbsUp, TrendingUp, CheckCircle2, Rocket, Target,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Modal, Input, Select } from "../../../components/shared/ui";
import {
  trustQualityApi, TQ_ENUMS,
  BadgeRule, HealthRule, RecalcJob, BadgeDefinition,
  BadgeCriterionInput, HealthComponentInput, HealthBandInput,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";

type Tab = "definitions" | "badges" | "health" | "recalc";

const opt = (v: string) => ({ value: v, label: v.replace(/_/g, " ") });

// Curated lucide icons for badges, keyed by the name stored in the badge's
// `icon` field. Keeping a fixed registry (rather than free-text) means every
// badge renders to a real component and the picker can preview them.
const BADGE_ICONS: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  award: Award, star: Star, shield: Shield, "shield-check": ShieldCheck, crown: Crown,
  trophy: Trophy, medal: Medal, gem: Gem, sparkles: Sparkles, "badge-check": BadgeCheck,
  flame: Flame, zap: Zap, heart: Heart, "thumbs-up": ThumbsUp, "trending-up": TrendingUp,
  "check-circle": CheckCircle2, rocket: Rocket, target: Target,
};
const BADGE_ICON_NAMES = Object.keys(BADGE_ICONS);

// Distinct, accessible badge colors. First entry is the default.
const BADGE_COLORS = [
  "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6", "#ef4444",
  "#14b8a6", "#ec4899", "#6366f1", "#f97316", "#64748b",
];

/** Renders a badge's lucide icon in its color inside a soft tinted chip. */
function BadgeIcon({ icon, color, size = 16 }: { icon?: string | null; color?: string | null; size?: number }) {
  const Cmp = BADGE_ICONS[icon ?? ""] ?? Award;
  const c = color || BADGE_COLORS[0];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: size + 12, height: size + 12, borderRadius: 8, flexShrink: 0,
      background: `${c}22`, border: `1px solid ${c}55` }}>
      <Cmp size={size} color={c} />
    </span>
  );
}

export default function TrustQualityPage() {
  const [tab, setTab] = useState<Tab>("badges");
  const badgeDefs = useApi(useCallback(() => trustQualityApi.listBadgeDefinitions(), []), []);
  const badgeRules = useApi(useCallback(() => trustQualityApi.listBadgeRules(), []), []);
  const healthRules = useApi(useCallback(() => trustQualityApi.listHealthRules(), []), []);
  const jobs = useApi(useCallback(() => trustQualityApi.listRecalcJobs(), []), []);
  const [busy, setBusy] = useState<string | null>(null);

  // Which config modal is open, if any — with the record being edited (if any).
  const [modal, setModal] = useState<
    | null
    | { type: "definition"; editing?: BadgeDefinition }
    | { type: "badge-rule"; editing?: BadgeRule }
    | { type: "health-formula"; editing?: HealthRule }
  >(null);

  // Activating/deactivating a rule is an audited change and the backend refuses a
  // blank reason, so the admin is asked for one before the call goes out.
  const [prompt, setPrompt] = useState<
    { kind: "badge" | "health"; id: string; label: string; activating: boolean } | null>(null);
  const [reason, setReason] = useState("");

  const applyToggle = useAction(async () => {
    if (!prompt || !reason.trim()) return;
    const { kind, id, activating } = prompt;
    setBusy(id);
    try {
      if (kind === "badge") {
        if (activating) await trustQualityApi.activateBadgeRule(id, reason.trim());
        else await trustQualityApi.deactivateBadgeRule(id, reason.trim());
        badgeRules.refetch();
      } else {
        if (activating) await trustQualityApi.activateHealthRule(id, reason.trim());
        else await trustQualityApi.deactivateHealthRule(id, reason.trim());
        healthRules.refetch();
      }
      setPrompt(null);
      setReason("");
    } finally { setBusy(null); }
  });

  const askReason = (kind: "badge" | "health", r: { id: string; status: string }, label: string) => {
    setReason("");
    setPrompt({ kind, id: r.id, label, activating: r.status !== "active" });
  };

  const runRecalc = useAction(async (kind: "badges" | "health" | "risk" | "all") => {
    setBusy(kind);
    try { await trustQualityApi.recalculate(kind); jobs.refetch(); }
    finally { setBusy(null); }
  });

  const statusBadge = (s: string) => (
    <Badge variant={s === "active" ? "success" : s === "completed" ? "success"
      : s === "failed" ? "danger" : s === "running" ? "info" : "muted"}>{s}</Badge>
  );

  // Look up a rule's badge definition so its icon/color show on the rule row.
  const defsById = useMemo(() => {
    const m: Record<string, BadgeDefinition> = {};
    for (const b of badgeDefs.data ?? []) m[b.id] = b;
    return m;
  }, [badgeDefs.data]);

  const TABS: { id: Tab; label: string }[] = [
    { id: "badges", label: "Badge Rules" },
    { id: "definitions", label: "Badges" },
    { id: "health", label: "Health Formulas" },
    { id: "recalc", label: "Recalculation" },
  ];

  return (
    <AdminLayout activeNav="providers">
      <RequirePermission requiredPermission="" parentLabel="Providers">
        <SectionHeader
          title="Trust & Quality"
          subtitle="Configure provider badges, award rules and health-score formulas, then recalculate. Badges and health band drive provider trust and commission."
          actions={
            tab === "badges" ? <Btn size="sm" onClick={() => setModal({ type: "badge-rule" })}>+ New Badge Rule</Btn>
            : tab === "definitions" ? <Btn size="sm" onClick={() => setModal({ type: "definition" })}>+ New Badge</Btn>
            : tab === "health" ? <Btn size="sm" onClick={() => setModal({ type: "health-formula" })}>+ New Health Formula</Btn>
            : undefined
          }
        />

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {TABS.map(t => (
            <Btn key={t.id} size="sm" variant={tab === t.id ? "primary" : "ghost"} onClick={() => setTab(t.id)}>
              {t.label}
            </Btn>
          ))}
        </div>

        {tab === "badges" && (
          <Card padding={0}>
            {badgeRules.loading ? <Spinner /> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 16px" }}>Badge</th>
                  <th style={{ padding: "10px 16px" }}>Rule</th>
                  <th style={{ padding: "10px 16px" }}>Criteria</th>
                  <th style={{ padding: "10px 16px" }}>Award</th>
                  <th style={{ padding: "10px 16px" }}>Status</th>
                  <th style={{ padding: "10px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {badgeRules.data?.map(r => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontWeight: 600 }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          <BadgeIcon icon={defsById[r.badge_id]?.icon} color={defsById[r.badge_id]?.color} />
                          {r.badge?.name ?? r.rule_key}
                          {r.badge?.customer_visible && <Badge variant="muted" size="sm">customer-visible</Badge>}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{r.rule_type?.replace(/_/g, " ")}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {(r.criteria ?? []).map(c => `${c.metric_key} ${c.operator.replace(/_/g, " ")} ${c.value}`).join("; ") || "—"}
                      </td>
                      <td style={{ padding: "10px 16px" }}>{r.auto_award ? "Auto" : "Manual"}</td>
                      <td style={{ padding: "10px 16px" }}>{statusBadge(r.status)}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ display: "inline-flex", gap: 6 }}>
                          <Btn size="sm" variant="ghost" onClick={() => setModal({ type: "badge-rule", editing: r })}>Edit</Btn>
                          <Btn size="sm" variant="secondary" disabled={busy === r.id}
                            onClick={() => askReason("badge", r, r.badge?.name ?? r.rule_key)}>
                            {r.status === "active" ? "Deactivate" : "Activate"}
                          </Btn>
                        </span>
                      </td>
                    </tr>
                  ))}
                  {badgeRules.data?.length === 0 && (
                    <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No badge rules — create one to start awarding badges.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {tab === "definitions" && (
          <Card padding={0}>
            {badgeDefs.loading ? <Spinner /> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 16px" }}>Badge</th>
                  <th style={{ padding: "10px 16px" }}>Key</th>
                  <th style={{ padding: "10px 16px" }}>Target</th>
                  <th style={{ padding: "10px 16px" }}>Visibility</th>
                  <th style={{ padding: "10px 16px" }}>Status</th>
                  <th style={{ padding: "10px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {badgeDefs.data?.map(b => (
                    <tr key={b.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontWeight: 600 }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          <BadgeIcon icon={b.icon} color={b.color} />
                          {b.name}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-tertiary)", fontFamily: "monospace", fontSize: 12 }}>{b.badge_key}</td>
                      <td style={{ padding: "10px 16px" }}>{b.target_type?.replace(/_/g, " ")}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12 }}>
                        {b.customer_visible && <Badge variant="info" size="sm">customer</Badge>}
                        {b.tenant_visible && <Badge variant="muted" size="sm">provider</Badge>}
                        {b.admin_only && <Badge variant="warning" size="sm">admin-only</Badge>}
                      </td>
                      <td style={{ padding: "10px 16px" }}>{statusBadge(b.status)}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <Btn size="sm" variant="ghost" onClick={() => setModal({ type: "definition", editing: b })}>Edit</Btn>
                      </td>
                    </tr>
                  ))}
                  {badgeDefs.data?.length === 0 && (
                    <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No badges defined.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {tab === "health" && (
          <Card padding={0}>
            {healthRules.loading ? <Spinner /> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "10px 16px" }}>Formula</th>
                  <th style={{ padding: "10px 16px" }}>Target</th>
                  <th style={{ padding: "10px 16px" }}>Score range</th>
                  <th style={{ padding: "10px 16px" }}>Status</th>
                  <th style={{ padding: "10px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {healthRules.data?.map(r => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 16px", fontWeight: 600 }}>{r.name}</td>
                      <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{r.target_type?.replace(/_/g, " ")}</td>
                      <td style={{ padding: "10px 16px" }}>{r.min_score}–{r.max_score} (base {r.base_score})</td>
                      <td style={{ padding: "10px 16px" }}>{statusBadge(r.status)}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ display: "inline-flex", gap: 6 }}>
                          <Btn size="sm" variant="ghost" onClick={() => setModal({ type: "health-formula", editing: r })}>Edit</Btn>
                          <Btn size="sm" variant="secondary" disabled={busy === r.id}
                            onClick={() => askReason("health", r, r.name)}>
                            {r.status === "active" ? "Deactivate" : "Activate"}
                          </Btn>
                        </span>
                      </td>
                    </tr>
                  ))}
                  {healthRules.data?.length === 0 && (
                    <tr><td colSpan={5} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No health formulas.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {tab === "recalc" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Run a recalculation</div>
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
                Re-evaluate every provider against the active rules. Recorded as a job below.
              </p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {(["badges", "health", "risk", "all"] as const).map(k => (
                  <Btn key={k} disabled={busy === k} onClick={() => runRecalc.execute(k)}>
                    {busy === k ? "Running…" : `Recalculate ${k}`}
                  </Btn>
                ))}
              </div>
            </Card>
            <Card padding={0}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 700, fontSize: 14 }}>
                Recent jobs
              </div>
              {jobs.loading ? <Spinner /> : (
                <div style={{ overflowX: "auto", maxHeight: 420, overflowY: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                      <th style={{ padding: "8px 16px" }}>Type</th>
                      <th style={{ padding: "8px 16px" }}>Status</th>
                      <th style={{ padding: "8px 16px" }}>Processed</th>
                      <th style={{ padding: "8px 16px" }}>By</th>
                      <th style={{ padding: "8px 16px" }}>When</th>
                    </tr></thead>
                    <tbody>
                      {jobs.data?.slice(0, 40).map(j => (
                        <tr key={j.id} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px 16px" }}>{j.job_type}</td>
                          <td style={{ padding: "8px 16px" }}>{statusBadge(j.status)}</td>
                          <td style={{ padding: "8px 16px" }}>
                            {j.processed_count}/{j.total_count}{j.failed_count ? ` (${j.failed_count} failed)` : ""}
                          </td>
                          <td style={{ padding: "8px 16px", color: "var(--text-tertiary)" }}>{j.triggered_by}</td>
                          <td style={{ padding: "8px 16px", color: "var(--text-tertiary)" }}>
                            {String(j.completed_at ?? j.started_at ?? "").replace("T", " ").slice(0, 19)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ── Config modals ─────────────────────────────────────────────── */}
        <BadgeDefinitionModal
          open={modal?.type === "definition"} onClose={() => setModal(null)}
          editing={modal?.type === "definition" ? modal.editing : undefined}
          onSaved={() => { setModal(null); badgeDefs.refetch(); }}
        />
        <BadgeRuleModal
          open={modal?.type === "badge-rule"} onClose={() => setModal(null)}
          editing={modal?.type === "badge-rule" ? modal.editing : undefined}
          badges={badgeDefs.data ?? []}
          onSaved={() => { setModal(null); badgeRules.refetch(); }}
        />
        <HealthFormulaModal
          open={modal?.type === "health-formula"} onClose={() => setModal(null)}
          editing={modal?.type === "health-formula" ? modal.editing : undefined}
          onSaved={() => { setModal(null); healthRules.refetch(); }}
        />

        {/* ── Reason prompt for activate/deactivate ─────────────────────── */}
        {prompt && (
          <Modal open onClose={() => setPrompt(null)}
            title={`${prompt.activating ? "Activate" : "Deactivate"} ${prompt.label}`} size="sm">
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
              This change is recorded in the audit trail. A reason is required.
            </p>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              placeholder="Why is this rule being changed?"
              style={{ width: "100%", padding: 10, fontSize: 13, fontFamily: "inherit",
                borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
              <Btn variant="ghost" onClick={() => setPrompt(null)}>Cancel</Btn>
              <Btn disabled={!reason.trim() || busy === prompt.id} onClick={() => applyToggle.execute()}>
                {busy === prompt.id ? "Saving…" : prompt.activating ? "Activate" : "Deactivate"}
              </Btn>
            </div>
          </Modal>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}

// ── Shared small pieces ───────────────────────────────────────────────────────

function ErrText({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "4px 0 0" }}>{msg}</p>;
}

const rowStyle: React.CSSProperties = {
  display: "grid", gap: 8, alignItems: "end", marginBottom: 8,
};

// ── Badge Definition modal ────────────────────────────────────────────────────

function BadgeDefinitionModal({ open, onClose, onSaved, editing }: {
  open: boolean; onClose: () => void; onSaved: () => void; editing?: BadgeDefinition;
}) {
  const [f, setF] = useState({
    badge_key: "", name: "", target_type: "tenant", customer_visible: true,
    icon: BADGE_ICON_NAMES[0], color: BADGE_COLORS[0],
  });
  const [err, setErr] = useState<string | null>(null);

  // Prefill when opened for editing; reset when opened fresh.
  React.useEffect(() => {
    if (!open) return;
    setErr(null);
    setF(editing ? {
      badge_key: editing.badge_key, name: editing.name, target_type: editing.target_type,
      customer_visible: editing.customer_visible,
      icon: editing.icon || BADGE_ICON_NAMES[0], color: editing.color || BADGE_COLORS[0],
    } : { badge_key: "", name: "", target_type: "tenant", customer_visible: true,
      icon: BADGE_ICON_NAMES[0], color: BADGE_COLORS[0] });
  }, [open, editing]);

  const save = useAction(async () => {
    setErr(null);
    try {
      if (editing) {
        await trustQualityApi.updateBadgeDefinition(editing.id, {
          name: f.name.trim(), customer_visible: f.customer_visible, icon: f.icon, color: f.color });
      } else {
        await trustQualityApi.createBadgeDefinition({
          badge_key: f.badge_key.trim(), name: f.name.trim(),
          target_type: f.target_type, customer_visible: f.customer_visible,
          icon: f.icon, color: f.color, status: "active" });
      }
      onSaved();
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed to save badge."); }
  });
  const valid = f.badge_key.trim() && f.name.trim();
  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit badge" : "New badge"} size="md">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Live preview of the icon + color the badge will carry. */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: 10,
          borderRadius: 8, background: "var(--surface-sunken)" }}>
          <BadgeIcon icon={f.icon} color={f.color} size={22} />
          <span style={{ fontWeight: 600 }}>{f.name || "Badge preview"}</span>
        </div>
        <Input label="Badge key" required value={f.badge_key} onChange={v => setF({ ...f, badge_key: v })}
          disabled={!!editing} hint={editing ? "Key is immutable" : "Unique machine key, e.g. top_rated_pro"} />
        <Input label="Display name" required value={f.name} onChange={v => setF({ ...f, name: v })} />
        <Select label="Target" value={f.target_type} onChange={v => setF({ ...f, target_type: v })}
          disabled={!!editing} options={TQ_ENUMS.badgeTargets.map(opt)} />

        <div>
          <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>Icon</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
            {BADGE_ICON_NAMES.map(name => {
              const Cmp = BADGE_ICONS[name];
              const sel = f.icon === name;
              return (
                <button key={name} type="button" onClick={() => setF({ ...f, icon: name })}
                  aria-label={name} style={{
                    width: 34, height: 34, borderRadius: 8, cursor: "pointer",
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    background: sel ? `${f.color}22` : "var(--surface)",
                    border: `1px solid ${sel ? f.color : "var(--border)"}` }}>
                  <Cmp size={16} color={sel ? f.color : "var(--text-tertiary)"} />
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>Color</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
            {BADGE_COLORS.map(c => (
              <button key={c} type="button" onClick={() => setF({ ...f, color: c })}
                aria-label={c} style={{
                  width: 26, height: 26, borderRadius: "50%", cursor: "pointer", background: c,
                  border: f.color === c ? "3px solid var(--text-primary)" : "2px solid var(--border)" }} />
            ))}
          </div>
        </div>

        <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
          <input type="checkbox" checked={f.customer_visible}
            onChange={e => setF({ ...f, customer_visible: e.target.checked })} />
          Visible to customers
        </label>
        <ErrText msg={err} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!valid} onClick={() => save.execute()}>{editing ? "Save changes" : "Create badge"}</Btn>
        </div>
      </div>
    </Modal>
  );
}

// ── Badge Rule modal (with criteria builder) ──────────────────────────────────

function BadgeRuleModal({ open, onClose, onSaved, badges, editing }: {
  open: boolean; onClose: () => void; onSaved: () => void; badges: BadgeDefinition[];
  editing?: BadgeRule;
}) {
  const [f, setF] = useState({ rule_key: "", badge_id: "", rule_type: "auto_award", auto_award: true });
  const [criteria, setCriteria] = useState<BadgeCriterionInput[]>([
    { metric_key: "", operator: "greater_than_or_equal", value: "", is_required: true },
  ]);
  const [err, setErr] = useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;
    setErr(null);
    if (editing) {
      setF({ rule_key: editing.rule_key, badge_id: editing.badge_id,
        rule_type: editing.rule_type, auto_award: editing.auto_award });
      setCriteria((editing.criteria ?? []).length
        ? editing.criteria!.map(c => ({ metric_key: c.metric_key, operator: c.operator,
            value: c.value, is_required: true }))
        : [{ metric_key: "", operator: "greater_than_or_equal", value: "", is_required: true }]);
    } else {
      setF({ rule_key: "", badge_id: "", rule_type: "auto_award", auto_award: true });
      setCriteria([{ metric_key: "", operator: "greater_than_or_equal", value: "", is_required: true }]);
    }
  }, [open, editing]);

  const selectedBadge = useMemo(() => badges.find(b => b.id === f.badge_id), [badges, f.badge_id]);

  const setCrit = (i: number, patch: Partial<BadgeCriterionInput>) =>
    setCriteria(cs => cs.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  const save = useAction(async () => {
    setErr(null);
    // Coerce numeric-looking criterion values to numbers; the engine compares
    // metric values numerically for the ordering operators.
    const cleaned = criteria
      .filter(c => c.metric_key.trim())
      .map(c => {
        const raw = String(c.value ?? "").trim();
        const num = Number(raw);
        return { ...c, metric_key: c.metric_key.trim(),
          value: raw !== "" && !Number.isNaN(num) ? num : raw };
      });
    try {
      if (editing) {
        await trustQualityApi.updateBadgeRule(editing.id, {
          badge_id: f.badge_id, rule_type: f.rule_type, auto_award: f.auto_award,
          target_type: selectedBadge?.target_type ?? editing.target_type, criteria: cleaned });
      } else {
        await trustQualityApi.createBadgeRule({
          rule_key: f.rule_key.trim(), badge_id: f.badge_id,
          target_type: selectedBadge?.target_type ?? "tenant",
          rule_type: f.rule_type, auto_award: f.auto_award,
          status: "draft", criteria: cleaned });
      }
      onSaved();
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed to save rule."); }
  });

  const valid = f.rule_key.trim() && f.badge_id;
  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit badge rule" : "New badge rule"} size="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {badges.length === 0 && (
          <div style={{ fontSize: 13, color: "var(--warning-text)", background: "var(--warning-bg)",
            padding: 10, borderRadius: 8 }}>
            Create a badge first (Badges tab) — a rule awards an existing badge.
          </div>
        )}
        <Input label="Rule key" required value={f.rule_key} onChange={v => setF({ ...f, rule_key: v })}
          disabled={!!editing} hint={editing ? "Key is immutable" : "Unique machine key, e.g. auto_top_rated"} />
        <Select label="Badge to award" value={f.badge_id} onChange={v => setF({ ...f, badge_id: v })}
          placeholder="Select a badge…"
          options={badges.map(b => ({ value: b.id, label: `${b.name} (${b.target_type})` }))} />
        <Select label="Rule type" value={f.rule_type} onChange={v => setF({ ...f, rule_type: v })}
          options={TQ_ENUMS.badgeRuleTypes.map(opt)} />
        <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
          <input type="checkbox" checked={f.auto_award}
            onChange={e => setF({ ...f, auto_award: e.target.checked })} />
          Award automatically when criteria are met
        </label>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, margin: "6px 0 8px" }}>Award criteria</div>
          {criteria.map((c, i) => (
            <div key={i} style={{ ...rowStyle, gridTemplateColumns: "1fr 1fr 0.8fr auto" }}>
              <Input label={i === 0 ? "Metric key" : undefined} value={c.metric_key}
                onChange={v => setCrit(i, { metric_key: v })} placeholder="average_rating" />
              <Select label={i === 0 ? "Operator" : undefined} value={c.operator}
                onChange={v => setCrit(i, { operator: v })} options={TQ_ENUMS.operators.map(opt)} />
              <Input label={i === 0 ? "Value" : undefined} value={String(c.value ?? "")}
                onChange={v => setCrit(i, { value: v })} placeholder="4.5" />
              <Btn size="sm" variant="ghost" onClick={() => setCriteria(cs => cs.filter((_, j) => j !== i))}>✕</Btn>
            </div>
          ))}
          <Btn size="sm" variant="secondary"
            onClick={() => setCriteria(cs => [...cs, { metric_key: "", operator: "greater_than_or_equal", value: "", is_required: true }])}>
            + Add criterion
          </Btn>
        </div>

        <ErrText msg={err} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!valid} onClick={() => save.execute()}>{editing ? "Save changes" : "Create rule (draft)"}</Btn>
        </div>
        {!editing && (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
            New rules are created as drafts. Activate them from the Badge Rules tab once reviewed.
          </p>
        )}
      </div>
    </Modal>
  );
}

// ── Health Formula modal (components + bands builder) ─────────────────────────

function HealthFormulaModal({ open, onClose, onSaved, editing }: {
  open: boolean; onClose: () => void; onSaved: () => void; editing?: HealthRule;
}) {
  const [f, setF] = useState({ formula_key: "", name: "", target_type: "tenant_provider" });
  const [components, setComponents] = useState<HealthComponentInput[]>([
    { metric_key: "", weight_percent: 100, direction: "positive", min_value: 0, max_value: 100 },
  ]);
  const [bands, setBands] = useState<HealthBandInput[]>([
    { band_key: "blocked", band_name: "Blocked", min_score: 0, max_score: 49 },
    { band_key: "healthy", band_name: "Healthy", min_score: 50, max_score: 100 },
  ]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // The list row has only scalars, so on edit fetch the full formula for its
  // components and bands.
  React.useEffect(() => {
    if (!open) return;
    setErr(null);
    if (!editing) {
      setF({ formula_key: "", name: "", target_type: "tenant_provider" });
      setComponents([{ metric_key: "", weight_percent: 100, direction: "positive", min_value: 0, max_value: 100 }]);
      setBands([{ band_key: "blocked", band_name: "Blocked", min_score: 0, max_score: 49 },
        { band_key: "healthy", band_name: "Healthy", min_score: 50, max_score: 100 }]);
      return;
    }
    setLoading(true);
    setF({ formula_key: editing.formula_key, name: editing.name, target_type: editing.target_type });
    trustQualityApi.getHealthFormula(editing.id).then(res => {
      const d = (res as { data?: Record<string, unknown> })?.data ?? (res as Record<string, unknown>);
      const comps = (d.components as Record<string, unknown>[] | undefined) ?? [];
      const bnds = (d.bands as Record<string, unknown>[] | undefined) ?? [];
      setComponents(comps.length ? comps.map(c => ({
        metric_key: String(c.metric_key), weight_percent: Number(c.weight_percent),
        direction: String(c.direction ?? "positive"),
        min_value: Number(c.min_value ?? 0), max_value: Number(c.max_value ?? 100),
      })) : [{ metric_key: "", weight_percent: 100, direction: "positive", min_value: 0, max_value: 100 }]);
      setBands(bnds.length ? bnds.map(b => ({
        band_key: String(b.band_key), band_name: String(b.band_name ?? b.band_key),
        min_score: Number(b.min_score), max_score: Number(b.max_score),
      })) : []);
    }).catch(() => setErr("Failed to load formula detail.")).finally(() => setLoading(false));
  }, [open, editing]);

  const totalWeight = components.reduce((s, c) => s + (Number(c.weight_percent) || 0), 0);

  const setComp = (i: number, patch: Partial<HealthComponentInput>) =>
    setComponents(cs => cs.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  const setBand = (i: number, patch: Partial<HealthBandInput>) =>
    setBands(bs => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));

  const save = useAction(async () => {
    setErr(null);
    const payload = {
      name: f.name.trim(), target_type: f.target_type,
      components: components.filter(c => c.metric_key.trim()).map(c => ({
        ...c, metric_key: c.metric_key.trim(), weight_percent: Number(c.weight_percent),
        min_value: Number(c.min_value), max_value: Number(c.max_value),
      })),
      bands: bands.map(b => ({ ...b, min_score: Number(b.min_score), max_score: Number(b.max_score) })),
    };
    try {
      if (editing) {
        await trustQualityApi.updateHealthFormula(editing.id, payload);
      } else {
        await trustQualityApi.createHealthFormula({
          formula_key: f.formula_key.trim(), base_score: 100, min_score: 0, max_score: 100,
          status: "draft", ...payload });
      }
      onSaved();
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed to save formula."); }
  });

  const valid = f.formula_key.trim() && f.name.trim() && components.some(c => c.metric_key.trim());
  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit health formula" : "New health formula"} size="xl">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <Input label="Formula key" required value={f.formula_key} onChange={v => setF({ ...f, formula_key: v })}
            disabled={!!editing} hint={editing ? "Key is immutable" : "e.g. provider_health_v2"} />
          <Input label="Name" required value={f.name} onChange={v => setF({ ...f, name: v })} />
          <Select label="Target" value={f.target_type} onChange={v => setF({ ...f, target_type: v })}
            disabled={!!editing} options={TQ_ENUMS.healthTargets.map(opt)} />
        </div>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, margin: "6px 0 8px",
            display: "flex", justifyContent: "space-between" }}>
            <span>Weighted components</span>
            <span style={{ color: Math.abs(totalWeight - 100) < 0.01 ? "var(--success-text)" : "var(--warning-text)" }}>
              Total weight: {totalWeight}% {Math.abs(totalWeight - 100) < 0.01 ? "✓" : "(must be 100 to activate)"}
            </span>
          </div>
          {components.map((c, i) => (
            <div key={i} style={{ ...rowStyle, gridTemplateColumns: "1.4fr 0.7fr 0.9fr auto" }}>
              <Input label={i === 0 ? "Metric key" : undefined} value={c.metric_key}
                onChange={v => setComp(i, { metric_key: v })} placeholder="job_completion_rate" />
              <Input label={i === 0 ? "Weight %" : undefined} type="number" value={String(c.weight_percent)}
                onChange={v => setComp(i, { weight_percent: Number(v) })} />
              <Select label={i === 0 ? "Direction" : undefined} value={c.direction ?? "positive"}
                onChange={v => setComp(i, { direction: v })} options={TQ_ENUMS.directions.map(opt)} />
              <Btn size="sm" variant="ghost" onClick={() => setComponents(cs => cs.filter((_, j) => j !== i))}>✕</Btn>
            </div>
          ))}
          <Btn size="sm" variant="secondary"
            onClick={() => setComponents(cs => [...cs, { metric_key: "", weight_percent: 0, direction: "positive", min_value: 0, max_value: 100 }])}>
            + Add component
          </Btn>
        </div>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, margin: "6px 0 8px" }}>Score bands (must cover 0–100)</div>
          {bands.map((b, i) => (
            <div key={i} style={{ ...rowStyle, gridTemplateColumns: "1fr 1fr 0.7fr 0.7fr auto" }}>
              <Input label={i === 0 ? "Band key" : undefined} value={b.band_key}
                onChange={v => setBand(i, { band_key: v })} placeholder="healthy" />
              <Input label={i === 0 ? "Band name" : undefined} value={b.band_name}
                onChange={v => setBand(i, { band_name: v })} />
              <Input label={i === 0 ? "Min" : undefined} type="number" value={String(b.min_score)}
                onChange={v => setBand(i, { min_score: Number(v) })} />
              <Input label={i === 0 ? "Max" : undefined} type="number" value={String(b.max_score)}
                onChange={v => setBand(i, { max_score: Number(v) })} />
              <Btn size="sm" variant="ghost" onClick={() => setBands(bs => bs.filter((_, j) => j !== i))}>✕</Btn>
            </div>
          ))}
          <Btn size="sm" variant="secondary"
            onClick={() => setBands(bs => [...bs, { band_key: "", band_name: "", min_score: 0, max_score: 0 }])}>
            + Add band
          </Btn>
        </div>

        <ErrText msg={err} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!valid || loading} onClick={() => save.execute()}>
            {loading ? "Loading…" : editing ? "Save changes" : "Create formula (draft)"}
          </Btn>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          {editing
            ? "Editing an active formula re-checks that weights total 100% and bands cover 0–100."
            : "New formulas are created as drafts. Component weights must total 100% and bands must cover 0–100 before the formula can be activated."}
        </p>
      </div>
    </Modal>
  );
}
