"use client";
/**
 * MODULE-L5-12 — Trust & Quality (badges, provider health, recalculation).
 *
 * The trust_quality engine was registered and live — provider badges, badge
 * award rules, health-score formulas and recalculation jobs, all with real
 * seeded config — but had NO admin UI at all. This is its management console.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner } from "../../../components/shared/ui";
import {
  trustQualityApi, BadgeRule, HealthRule, RecalcJob,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RequirePermission } from "../../../components/shared/PermissionGate";

type Tab = "badges" | "health" | "recalc";

export default function TrustQualityPage() {
  const [tab, setTab] = useState<Tab>("badges");
  const badgeRules = useApi(useCallback(() => trustQualityApi.listBadgeRules(), []), []);
  const healthRules = useApi(useCallback(() => trustQualityApi.listHealthRules(), []), []);
  const jobs = useApi(useCallback(() => trustQualityApi.listRecalcJobs(), []), []);
  const [busy, setBusy] = useState<string | null>(null);

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

  return (
    <AdminLayout activeNav="providers">
      <RequirePermission requiredPermission="" parentLabel="Providers">
        <SectionHeader
          title="Trust & Quality"
          subtitle="Provider badges, health-score formulas and recalculation. Badges and health drive provider trust and (via health band) commission."
        />

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {(["badges", "health", "recalc"] as Tab[]).map(t => (
            <Btn key={t} size="sm" variant={tab === t ? "primary" : "ghost"} onClick={() => setTab(t)}>
              {t === "badges" ? "Badge Rules" : t === "health" ? "Health Formulas" : "Recalculation"}
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
                        {r.badge?.name ?? r.rule_key}
                        {r.badge?.customer_visible && <Badge variant="muted" size="sm">customer-visible</Badge>}
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>{r.rule_type?.replace(/_/g, " ")}</td>
                      <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {(r.criteria ?? []).map(c => `${c.metric_key} ${c.operator.replace(/_/g, " ")} ${c.value}`).join("; ") || "—"}
                      </td>
                      <td style={{ padding: "10px 16px" }}>{r.auto_award ? "Auto" : "Manual"}</td>
                      <td style={{ padding: "10px 16px" }}>{statusBadge(r.status)}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <Btn size="sm" variant="secondary" disabled={busy === r.id}
                          onClick={() => askReason("badge", r, r.badge?.name ?? r.rule_key)}>
                          {r.status === "active" ? "Deactivate" : "Activate"}
                        </Btn>
                      </td>
                    </tr>
                  ))}
                  {badgeRules.data?.length === 0 && (
                    <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>No badge rules.</td></tr>
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
                        <Btn size="sm" variant="secondary" disabled={busy === r.id}
                          onClick={() => askReason("health", r, r.name)}>
                          {r.status === "active" ? "Deactivate" : "Activate"}
                        </Btn>
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

        {prompt && (
          <div onClick={() => setPrompt(null)} style={{ position: "fixed", inset: 0,
            background: "rgba(0,0,0,0.45)", zIndex: 300,
            display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div onClick={e => e.stopPropagation()} style={{ width: "min(460px, 94vw)",
              background: "var(--surface)", borderRadius: 12, padding: 22,
              boxShadow: "0 8px 40px rgba(0,0,0,0.3)" }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                {prompt.activating ? "Activate" : "Deactivate"} {prompt.label}
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 14px" }}>
                This change is recorded in the audit trail. A reason is required.
              </p>
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                rows={3}
                placeholder="Why is this rule being changed?"
                style={{ width: "100%", padding: 10, fontSize: 13, fontFamily: "inherit",
                  borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--bg)", color: "var(--text-primary)", resize: "vertical" }}
              />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
                <Btn variant="ghost" onClick={() => setPrompt(null)}>Cancel</Btn>
                <Btn disabled={!reason.trim() || busy === prompt.id}
                  onClick={() => applyToggle.execute()}>
                  {busy === prompt.id ? "Saving…" : prompt.activating ? "Activate" : "Deactivate"}
                </Btn>
              </div>
            </div>
          </div>
        )}
      </RequirePermission>
    </AdminLayout>
  );
}
