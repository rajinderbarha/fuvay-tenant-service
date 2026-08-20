"use client";
/**
 * MODULE-L5-12 â€” Trust & Quality (badges, provider health, recalculation).
 *
 * The trust_quality engine was registered and live â€” provider badges, badge
 * award rules, health-score formulas and recalculation jobs, all with real
 * seeded config â€” but had NO admin UI at all. This is its management console.
 *
 * The admin configures the engine here: the fixed trust badge catalog, badge
 * award rules (with metric criteria), and health-score formulas (with weighted
 * components and score bands), then activating/deactivating and recalculating.
 */
import React, { useCallback, useMemo, useState } from "react";
import {
  Award, Star, Shield, ShieldCheck, Crown, Trophy, Medal, Gem, Sparkles,
  BadgeCheck, Flame, Zap, Heart, ThumbsUp, TrendingUp, CheckCircle2, Rocket, Target,
  Gauge, Activity,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Modal, Input, Select, StatCard } from "../../../components/shared/ui";
import {
  trustQualityApi, TQ_ENUMS,
  BadgeRule, HealthRule, BadgeDefinition,
  BadgeCriterionInput, HealthComponentInput, HealthBandInput,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";
import { ScoresTab } from "./ScoresTab";
import { AuditTab } from "./AuditTab";
import { RecalcTab } from "./RecalcTab";
import { EarnedTab } from "./EarnedTab";
import { BadgeRuleSimulator, HealthFormulaSimulator } from "./Simulate";

type Tab = "definitions" | "badges" | "health" | "scores" | "recalc" | "earned" | "audit";

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
// Distinct, accessible badge colors. First entry is the default.
const BADGE_COLORS = [
  "var(--warning)", "var(--brand)", "var(--success)", "#8b5cf6", "#ef4444",
  "#14b8a6", "#ec4899", "#6366f1", "#f97316", "#64748b",
];

/** Renders a badge's lucide icon in its color inside a soft tinted chip. */
function BadgeIcon({ icon, color, size = 16 }: { icon?: string | null; color?: string | null; size?: number }) {
  const Cmp = BADGE_ICONS[icon ?? ""] ?? Award;
  const c = color || BADGE_COLORS[0];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: size + 12, height: size + 12, borderRadius:"var(--radius-md)", flexShrink: 0,
      background: `${c}22`, border: `1px solid ${c}55` }}>
      <Cmp size={size} color={c} />
    </span>
  );
}

export default function TrustQualityPage() {
  const [tab, setTab] = useState<Tab>("scores");
  const badgeDefs = useApi(useCallback(() => trustQualityApi.listBadgeDefinitions(), []), []);
  const badgeRules = useApi(useCallback(() => trustQualityApi.listBadgeRules(), []), []);
  const healthRules = useApi(useCallback(() => trustQualityApi.listHealthRules(), []), []);
  const overview = useApi(useCallback(() => trustQualityApi.overview(), []), []);
  const [busy, setBusy] = useState<string | null>(null);

  // Which config modal is open, if any â€” with the record being edited (if any).
  const [modal, setModal] = useState<
    | null
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

  const statusBadge = (s: string) => (
    <Badge variant={s === "active" ? "success" : s === "completed" ? "success"
      : s === "failed" ? "danger" : s === "running" ? "info" : "muted"}>{s}</Badge>
  );

  // Look up a rule's badge definition so its icon/color show on the rule row.
  const defsById = useMemo(() => {
    const m: Record<string, BadgeDefinition> = {};
    for (const b of badgeDefs.data ?? []) if (b.id) m[b.id] = b;
    return m;
  }, [badgeDefs.data]);

  // Output first, then the configuration that produces it: an admin opening this
  // console almost always wants to know who scored what, not to edit a formula.
  const TABS: { id: Tab; label: string }[] = [
    { id: "scores", label: "Health Scores" },
    { id: "badges", label: "Badge Rules" },
    { id: "definitions", label: "Badge Catalog" },
    { id: "health", label: "Health Formulas" },
    { id: "earned", label: "Earned (by target)" },
    { id: "recalc", label: "Recalculation" },
    { id: "audit", label: "Audit Trail" },
  ];

  const badgeGroups = useMemo(() => {
    const labels: Record<string, string> = {
      tenant: "Tenant / provider badges",
      staff: "Staff badges",
      technician: "Technician badges",
    };
    return TQ_ENUMS.badgeTargets.map(target => ({
      target,
      label: labels[target] ?? target.replace(/_/g, " "),
      items: (badgeDefs.data ?? [])
        .filter(b => b.target_type === target)
        .sort((a, b) => (a.level ?? 99) - (b.level ?? 99)),
    }));
  }, [badgeDefs.data]);

  const activeSeededBadges = useMemo(
    () => (badgeDefs.data ?? []).filter((b): b is BadgeDefinition & { id: string } =>
      Boolean(b.id) && b.status === "active"),
    [badgeDefs.data],
  );

  const seedCatalog = useAction(async () => {
    await trustQualityApi.seedDefaults();
    badgeDefs.refetch();
    badgeRules.refetch();
    overview.refetch();
  });

  return (
    <AdminLayout activeNav="providers">
      {/* The gate previously passed an empty string, which RequirePermission
          treats as "always allow" â€” so this console, which changes commission
          bands and customer-visible trust, was open to any signed-in admin. */}
      <RequirePermission requiredPermission="trust_quality:read" parentLabel="Providers">
        <SectionHeader
          title="Trust & Quality"
          subtitle="Manage the customer-facing trust catalog, badge award rules and the health formulas consumed by provider matching."
          actions={
            tab === "badges" ? <Btn size="sm" onClick={() => setModal({ type: "badge-rule" })}>+ New Badge Rule</Btn>
            : tab === "health" ? <Btn size="sm" onClick={() => setModal({ type: "health-formula" })}>+ New Health Formula</Btn>
            : undefined
          }
        />

        {/* Headline counts across the live badge and health engines. Every figure is an aggregate
            computed in SQL, so this row costs one query regardless of platform size. */}
        <div style={{ display: "grid", gap: 12, marginBottom: 16,
          gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}>
          <StatCard label="Targets scored" value={(overview.data?.scored_targets ?? 0).toLocaleString()}
            icon={<Gauge size={16} />} />
          <StatCard label="Unbanded" value={(overview.data?.unbanded_targets ?? 0).toLocaleString()}
            icon={<Activity size={16} />}
            alert={(overview.data?.unbanded_targets ?? 0) > 0}
            change="too little data to band" />
          <StatCard label="Badges held" value={(overview.data?.badges_held ?? 0).toLocaleString()}
            icon={<Award size={16} />}
            change={`${overview.data?.active_badges ?? 0} badges · ${overview.data?.active_badge_rules ?? 0} rules`} />
          <StatCard label="Sweeps in flight" value={(overview.data?.jobs_in_flight ?? 0).toLocaleString()}
            icon={<TrendingUp size={16} />}
            change={`${overview.data?.active_formulas ?? 0} active formulas`} />
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
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
                    <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No badge rules — sync the fixed catalog to restore defaults.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {tab === "definitions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 800 }}>Fixed customer trust catalog</div>
                  <p style={{ margin: "6px 0 0", color: "var(--text-tertiary)", fontSize: 13, maxWidth: 760 }}>
                    Badge identities are no longer free-form. Tenant, staff and technician each have four
                    customer-safe trust levels. Admins configure the rules that award them; the visual
                    language stays consistent for customers across the platform.
                  </p>
                </div>
                <Btn size="sm" variant="secondary" disabled={seedCatalog.loading}
                  onClick={() => seedCatalog.execute()}>
                  {seedCatalog.loading ? "Syncing..." : "Sync fixed catalog"}
                </Btn>
              </div>
              {seedCatalog.error && (
                <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "10px 0 0" }}>{seedCatalog.error}</p>
              )}
            </Card>
            {badgeDefs.loading ? <Spinner /> : badgeGroups.map(group => (
              <Card key={group.target}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 800 }}>{group.label}</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                      {group.items.length} of 4 fixed badges configured
                    </div>
                  </div>
                  <Badge variant={group.items.length === 4 ? "success" : "warning"}>
                    {group.items.length === 4 ? "Complete" : "Needs sync"}
                  </Badge>
                </div>
                <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
                  {group.items.map(b => <TrustBadgeCard key={b.badge_key} badge={b} BadgeIcon={BadgeIcon} />)}
                </div>
              </Card>
            ))}
          </div>
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

        {tab === "scores" && <ScoresTab formulas={healthRules.data ?? []} />}

        {tab === "recalc" && <RecalcTab />}

        {tab === "audit" && <AuditTab />}

        {tab === "earned" && (
          <EarnedTab badges={activeSeededBadges} BadgeIcon={BadgeIcon} />
        )}

        {/* â”€â”€ Config modals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        <BadgeRuleModal
          open={modal?.type === "badge-rule"} onClose={() => setModal(null)}
          editing={modal?.type === "badge-rule" ? modal.editing : undefined}
          badges={activeSeededBadges}
          onSaved={() => { setModal(null); badgeRules.refetch(); }}
        />
        <HealthFormulaModal
          open={modal?.type === "health-formula"} onClose={() => setModal(null)}
          editing={modal?.type === "health-formula" ? modal.editing : undefined}
          onSaved={() => { setModal(null); healthRules.refetch(); }}
        />

        {/* â”€â”€ Reason prompt for activate/deactivate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        {prompt && (
          <Modal open onClose={() => setPrompt(null)}
            title={`${prompt.activating ? "Activate" : "Deactivate"} ${prompt.label}`} size="sm">
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
              This change is recorded in the audit trail. A reason is required.
            </p>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              placeholder="Why is this rule being changed?"
              style={{ width: "100%", padding: 10, fontSize: 13, fontFamily: "inherit",
                borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--surface)", color: "var(--text-primary)", resize: "vertical", boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
              <Btn variant="ghost" onClick={() => setPrompt(null)}>Cancel</Btn>
              <Btn disabled={!reason.trim() || busy === prompt.id} onClick={() => applyToggle.execute()}>
                {busy === prompt.id ? "Saving..." : prompt.activating ? "Activate" : "Deactivate"}
              </Btn>
            </div>
          </Modal>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}

// â”€â”€ Shared small pieces â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function ErrText({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "4px 0 0" }}>{msg}</p>;
}

const rowStyle: React.CSSProperties = {
  display: "grid", gap: 8, alignItems: "end", marginBottom: 8,
};

function TrustBadgeCard({ badge, BadgeIcon }: {
  badge: BadgeDefinition;
  BadgeIcon: React.ComponentType<{ icon?: string | null; color?: string | null; size?: number }>;
}) {
  const color = badge.color || "var(--brand)";
  return (
    <div style={{
      position: "relative",
      overflow: "hidden",
      minHeight: 150,
      padding: 16,
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      background: `linear-gradient(135deg, ${color}1f, var(--surface) 52%)`,
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{ position: "absolute", top: -28, right: -24, width: 96, height: 96,
        borderRadius: "50%", background: `${color}22` }} />
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <BadgeIcon icon={badge.icon} color={color} size={24} />
        <Badge variant={badge.status === "active" ? "success" : badge.status === "missing" ? "warning" : "muted"} size="sm">
          {badge.status === "missing" ? "not seeded" : badge.status}
        </Badge>
      </div>
      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase",
          color: "var(--text-tertiary)", fontWeight: 800 }}>
          Level {badge.level ?? "-"}
        </div>
        <div style={{ fontSize: 16, fontWeight: 850, marginTop: 3 }}>{badge.name}</div>
        <p style={{ margin: "6px 0 0", color: "var(--text-tertiary)", fontSize: 12, lineHeight: 1.45 }}>
          {badge.description || "Fixed platform trust badge."}
        </p>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 12 }}>
        {badge.customer_visible && <Badge variant="info" size="sm">customer visible</Badge>}
        {badge.tenant_visible && <Badge variant="muted" size="sm">provider visible</Badge>}
        <Badge variant="muted" size="sm">{badge.badge_key}</Badge>
      </div>
    </div>
  );
}


// â”€â”€ Badge Rule modal (with criteria builder) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
  const selectableBadges = useMemo(
    () => badges.filter((b): b is BadgeDefinition & { id: string } => Boolean(b.id)),
    [badges],
  );

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
            padding: 10, borderRadius:"var(--radius-md)" }}>
            Sync the fixed badge catalog first — a rule awards one of the approved badges.
          </div>
        )}
        <Input label="Rule key" required value={f.rule_key} onChange={v => setF({ ...f, rule_key: v })}
          disabled={!!editing} hint={editing ? "Key is immutable" : "Unique machine key, e.g. auto_top_rated"} />
        <Select label="Badge to award" value={f.badge_id} onChange={v => setF({ ...f, badge_id: v })}
          placeholder="Select a badge..."
          options={selectableBadges.map(b => ({ value: b.id, label: `${b.name} (${b.target_type})` }))} />
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
              <Btn size="sm" variant="ghost" onClick={() => setCriteria(cs => cs.filter((_, j) => j !== i))}>×</Btn>
            </div>
          ))}
          <Btn size="sm" variant="secondary"
            onClick={() => setCriteria(cs => [...cs, { metric_key: "", operator: "greater_than_or_equal", value: "", is_required: true }])}>
            + Add criterion
          </Btn>
        </div>

        {/* Simulation runs against the SAVED rule, so it is only offered when
            editing â€” on a new rule there is nothing on the server to simulate yet. */}
        {editing && (
          <BadgeRuleSimulator ruleId={editing.id}
            metricKeys={Array.from(new Set(criteria.map(c => c.metric_key.trim()).filter(Boolean)))} />
        )}

        <ErrText msg={err} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!valid} onClick={() => save.execute()}>{editing ? "Save changes" : "Create rule (draft)"}</Btn>
        </div>
        {!editing && (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
            New rules are created as drafts. Activate them from the Badge Rules tab once reviewed.
            Save first to try the rule out against sample metrics.
          </p>
        )}
      </div>
    </Modal>
  );
}

// â”€â”€ Health Formula modal (components + bands builder) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function HealthFormulaModal({ open, onClose, onSaved, editing }: {
  open: boolean; onClose: () => void; onSaved: () => void; editing?: HealthRule;
}) {
  const [f, setF] = useState({ formula_key: "", name: "", target_type: "tenant" });
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
      setF({ formula_key: "", name: "", target_type: "tenant" });
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
              <Btn size="sm" variant="ghost" onClick={() => setComponents(cs => cs.filter((_, j) => j !== i))}>×</Btn>
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
              <Btn size="sm" variant="ghost" onClick={() => setBands(bs => bs.filter((_, j) => j !== i))}>×</Btn>
            </div>
          ))}
          <Btn size="sm" variant="secondary"
            onClick={() => setBands(bs => [...bs, { band_key: "", band_name: "", min_score: 0, max_score: 0 }])}>
            + Add band
          </Btn>
        </div>

        {/* Simulation runs against the SAVED formula, so it is only offered when
            editing. Health bands gate commission, which makes a dry run before
            activation the difference between a considered change and a guess. */}
        {editing && (
          <HealthFormulaSimulator formulaId={editing.id}
            metricKeys={Array.from(new Set(components.map(c => c.metric_key.trim()).filter(Boolean)))} />
        )}

        <ErrText msg={err} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!valid || loading} onClick={() => save.execute()}>
            {loading ? "Loading..." : editing ? "Save changes" : "Create formula (draft)"}
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
