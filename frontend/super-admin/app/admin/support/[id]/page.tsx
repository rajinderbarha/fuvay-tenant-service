"use client";
// SUPER-ADMIN TENANT SUPPORT REQUEST — 360 detail + triage console.
// Every action maps 1:1 to a real route on app/engines/support/admin_router.py.
// Internal notes are rendered with an explicit internal-only treatment because
// the backend never returns them on any tenant endpoint.
import React, { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { Badge, Btn, Card, Skeleton } from "../../../../components/shared/ui";
import { ApiErrorState } from "../../../../components/shared/ApiStates";
import { supportAdminApi, ServiceOSError, SupportTicketDetail } from "../../../../lib/api";

const PRIORITIES = ["low", "normal", "high", "urgent", "critical"];
const PRIORITY_VARIANT: Record<string, "muted" | "default" | "warning" | "danger"> = {
  low: "muted", normal: "default", high: "warning", urgent: "danger", critical: "danger",
};
const BREACH_VARIANT: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  on_track: "success", at_risk: "warning", breached: "danger",
  paused: "info", met: "success", not_applicable: "muted",
};
const STATUS_LABELS: Record<string, string> = {
  draft: "Draft", submitted: "Submitted", triaged: "Triaged", assigned: "Assigned",
  investigating: "Investigating", waiting_for_tenant: "Awaiting tenant reply",
  waiting_for_serviceos: "With ServiceOS support", resolved: "Resolved",
  closed: "Closed", reopened: "Reopened", withdrawn: "Withdrawn",
};

function fmt(ts: string | null | undefined) {
  return ts ? ts.replace("T", " ").slice(0, 16) : "—";
}

export default function AdminSupportDetailPage() {
  const params = useParams<{ id: string }>();
  const id = String(params?.id ?? "");
  const router = useRouter();

  const [t, setT] = useState<SupportTicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<ServiceOSError | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionErr, setActionErr] = useState<string | null>(null);

  const [reply, setReply] = useState("");
  const [internal, setInternal] = useState(false);
  const [requestInfo, setRequestInfo] = useState(false);
  const [assignName, setAssignName] = useState("");
  const [assignTeam, setAssignTeam] = useState("");
  const [prio, setPrio] = useState("");
  const [prioReason, setPrioReason] = useState("");
  const [transitionReason, setTransitionReason] = useState("");
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [mergeId, setMergeId] = useState("");
  const [mergeReason, setMergeReason] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true); setErr(null);
    try { setT(await supportAdminApi.detail(id)); }
    catch (e) { setErr(e as ServiceOSError); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  const run = async (fn: () => Promise<SupportTicketDetail>) => {
    setBusy(true); setActionErr(null);
    try { setT(await fn()); }
    catch (e) { setActionErr((e as ServiceOSError).message); }
    finally { setBusy(false); }
  };

  const inp: React.CSSProperties = {
    height: 34, padding: "0 10px", borderRadius: 9, fontSize: 12, width: "100%",
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontFamily: "inherit",
  };
  const sectionTitle: React.CSSProperties = { margin: "0 0 10px", fontSize: 13, fontWeight: 700, color: "var(--text-primary)" };

  if (loading) {
    return <AdminLayout><PageShell><Card><Skeleton height={220} /></Card></PageShell></AdminLayout>;
  }
  if (err || !t) {
    return <AdminLayout><PageShell>
      <ApiErrorState error={err ?? "Support request not found."} onRetry={() => void load()} />
    </PageShell></AdminLayout>;
  }

  return (
    <AdminLayout>
      <PageShell>
        <PageHeader
          title={t.subject}
          description={`${t.ticket_number} · ${t.category_label}${t.subcategory ? ` / ${t.subcategory}` : ""} · reported by ${t.reporter_name ?? "—"} (${t.reporter_role ?? "tenant"})`}
          actions={<>
            <Btn variant="secondary" size="sm" onClick={() => router.push("/admin/support")}>Back to queue</Btn>
            <Btn variant="secondary" size="sm" onClick={() => void load()}>Refresh</Btn>
          </>}
        />

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <Badge variant="muted">{t.status_label}</Badge>
          <Badge variant={PRIORITY_VARIANT[t.priority] ?? "default"}>{t.priority}</Badge>
          <Badge variant={BREACH_VARIANT[t.sla.breach_state] ?? "muted"} dot>
            {t.sla.breach_state.replace(/_/g, " ")}
          </Badge>
          {t.is_critical_incident && <Badge variant="danger">critical incident channel</Badge>}
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            Tenant {t.tenant_id} · created {fmt(t.created_at)}
          </span>
        </div>

        {actionErr && <Card style={{ borderColor: "var(--danger-border)", background: "var(--danger-bg)" }} padding={12}>
          <span style={{ fontSize: 12, color: "var(--danger-text)" }}>{actionErr}</span>
        </Card>}

        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 2fr) minmax(280px, 1fr)", alignItems: "start" }}>
          {/* ── Conversation ─────────────────────────────────────────── */}
          <div style={{ display: "grid", gap: 16 }}>
            <Card>
              <h3 style={sectionTitle}>Reported problem</h3>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>{t.description}</p>
              <div style={{ marginTop: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
                Impact: {t.impact_label}
                {t.affected_feature ? ` · Feature: ${t.affected_feature}` : ""}
                {t.started_at ? ` · Started ${fmt(t.started_at)}` : ""}
              </div>
            </Card>

            <Card>
              <h3 style={sectionTitle}>Conversation</h3>
              <div style={{ display: "grid", gap: 10 }}>
                {t.conversation.map(m => {
                  const isInternal = m.visibility === "internal" || m.kind === "internal_note";
                  const isTenant = m.author_type === "tenant";
                  return (
                    <div key={m.id} style={{
                      border: `1px solid ${isInternal ? "var(--warning-border)" : "var(--border)"}`,
                      background: isInternal ? "var(--warning-bg)" : isTenant ? "var(--surface-sunken)" : "var(--surface)",
                      borderLeft: `3px solid ${isInternal ? "var(--warning-text)" : isTenant ? "var(--accent)" : "var(--brand, var(--accent))"}`,
                      borderRadius: 10, padding: "10px 12px",
                    }}>
                      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{m.author_name}</span>
                        <Badge size="sm" variant={isTenant ? "info" : m.author_type === "system" ? "muted" : "default"}>
                          {m.author_type}
                        </Badge>
                        {isInternal && <Badge size="sm" variant="warning">🔒 Internal note — never shown to the tenant</Badge>}
                        {m.kind === "information_request" && <Badge size="sm" variant="info">information request</Badge>}
                        <span style={{ fontSize: 11, color: "var(--text-tertiary)", marginLeft: "auto" }}>{fmt(m.created_at)}</span>
                      </div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>{m.body}</div>
                    </div>
                  );
                })}
                {t.conversation.length === 0 && (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No messages yet.</p>
                )}
              </div>

              <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <textarea value={reply} onChange={e => setReply(e.target.value)} rows={3}
                  placeholder={internal ? "Internal note — visible only to ServiceOS staff" : "Reply to the tenant…"}
                  style={{ ...inp, height: "auto", padding: 10, resize: "vertical",
                    borderColor: internal ? "var(--warning-border)" : "var(--border)",
                    background: internal ? "var(--warning-bg)" : "var(--surface)" }} />
                <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
                  <label style={{ fontSize: 12, display: "flex", gap: 5, alignItems: "center", color: "var(--text-secondary)" }}>
                    <input type="checkbox" checked={internal}
                      onChange={e => { setInternal(e.target.checked); if (e.target.checked) setRequestInfo(false); }} />
                    Internal note (not sent to tenant)
                  </label>
                  <label style={{ fontSize: 12, display: "flex", gap: 5, alignItems: "center", color: "var(--text-secondary)" }}>
                    <input type="checkbox" checked={requestInfo} disabled={internal}
                      onChange={e => setRequestInfo(e.target.checked)} />
                    Request information from the tenant (pauses SLA)
                  </label>
                  <Btn size="sm" loading={busy} disabled={!reply.trim()} style={{ marginLeft: "auto" }}
                    onClick={() => void run(async () => {
                      const d = await supportAdminApi.reply(t.id, { body: reply, internal, request_info: requestInfo });
                      setReply(""); setRequestInfo(false);
                      return d;
                    })}>
                    {internal ? "Add internal note" : requestInfo ? "Request information" : "Send reply"}
                  </Btn>
                </div>
              </div>
            </Card>

            <Card>
              <h3 style={sectionTitle}>Audit trail</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {t.status_history.map(e => (
                  <div key={e.id} style={{ display: "flex", gap: 10, fontSize: 12 }}>
                    <span style={{ color: "var(--text-tertiary)", minWidth: 120 }}>{fmt(e.created_at)}</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)", minWidth: 150 }}>{e.event_type}</span>
                    <span style={{ color: "var(--text-secondary)" }}>
                      {e.from || e.to ? `${e.from ?? "—"} → ${e.to ?? "—"}` : ""}{e.reason ? ` · ${e.reason}` : ""}
                      {e.actor_name ? ` · ${e.actor_name}` : ""} ({e.actor_type})
                    </span>
                  </div>
                ))}
                {t.status_history.length === 0 && (
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No audit events.</p>
                )}
              </div>
            </Card>
          </div>

          {/* ── Triage sidebar ───────────────────────────────────────── */}
          <div style={{ display: "grid", gap: 16 }}>
            <Card>
              <h3 style={sectionTitle}>SLA</h3>
              <p style={{ margin: "0 0 8px", fontSize: 12, color: "var(--text-secondary)" }}>{t.sla.display_message}</p>
              <dl style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", display: "grid", gap: 4 }}>
                <div>Policy: {t.sla.sla_policy}</div>
                <div>First response: {fmt(t.sla.first_response_due_at)} ({t.sla.first_response_state})</div>
                <div>Next update: {fmt(t.sla.next_update_due_at)} ({t.sla.next_update_state})</div>
                <div>Resolution target: {fmt(t.sla.resolution_target_at)} ({t.sla.resolution_state})</div>
                {t.sla.paused && <div>Paused at {fmt(t.sla.paused_at)}</div>}
              </dl>
              {t.priority_reasons.length > 0 && (
                <div style={{ marginTop: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
                  <strong style={{ color: "var(--text-secondary)" }}>Priority derivation</strong>
                  <ul style={{ margin: "4px 0 0", paddingLeft: 16 }}>
                    {t.priority_reasons.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
            </Card>

            <Card>
              <h3 style={sectionTitle}>Assign</h3>
              <div style={{ display: "grid", gap: 8 }}>
                <input value={assignName} onChange={e => setAssignName(e.target.value)}
                  placeholder="Assignee name" style={inp} />
                <input value={assignTeam} onChange={e => setAssignTeam(e.target.value)}
                  placeholder="Team (e.g. platform-ops)" style={inp} />
                <Btn size="sm" loading={busy} disabled={!assignName.trim() && !assignTeam.trim()}
                  onClick={() => void run(async () => {
                    const d = await supportAdminApi.assign(t.id, {
                      assignee_name: assignName.trim() || undefined,
                      team: assignTeam.trim() || undefined,
                    });
                    setAssignName(""); setAssignTeam("");
                    return d;
                  })}>Assign</Btn>
              </div>
              <p style={{ margin: "8px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                Currently: {t.assigned_admin_name ?? "unassigned"}{t.assigned_team ? ` · ${t.assigned_team}` : ""}
              </p>
            </Card>

            <Card>
              <h3 style={sectionTitle}>Change priority</h3>
              <div style={{ display: "grid", gap: 8 }}>
                <select value={prio} onChange={e => setPrio(e.target.value)} style={inp}>
                  <option value="">Select priority…</option>
                  {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <input value={prioReason} onChange={e => setPrioReason(e.target.value)}
                  placeholder="Reason (required, min 3 chars)" style={inp} />
                <Btn size="sm" loading={busy} disabled={!prio || prioReason.trim().length < 3}
                  onClick={() => void run(async () => {
                    const d = await supportAdminApi.setPriority(t.id, { priority: prio, reason: prioReason });
                    setPrio(""); setPrioReason("");
                    return d;
                  })}>Apply priority</Btn>
              </div>
            </Card>

            <Card>
              <h3 style={sectionTitle}>Move status</h3>
              {t.allowed_transitions.length === 0 ? (
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>
                  No further transitions are allowed from “{t.status_label}”.
                </p>
              ) : (
                <div style={{ display: "grid", gap: 8 }}>
                  <input value={transitionReason} onChange={e => setTransitionReason(e.target.value)}
                    placeholder="Reason (optional)" style={inp} />
                  {t.allowed_transitions.includes("resolved") && (
                    <textarea value={resolutionSummary} onChange={e => setResolutionSummary(e.target.value)} rows={2}
                      placeholder="Resolution summary (sent to the tenant on resolve)"
                      style={{ ...inp, height: "auto", padding: 10, resize: "vertical" }} />
                  )}
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {t.allowed_transitions.map(s => (
                      <Btn key={s} size="xs" loading={busy}
                        variant={s === "resolved" ? "success" : s === "reopened" ? "warning" : "secondary"}
                        onClick={() => void run(async () => {
                          const d = await supportAdminApi.transition(t.id, {
                            to_status: s,
                            reason: transitionReason.trim() || undefined,
                            resolution_summary: s === "resolved" ? (resolutionSummary.trim() || undefined) : undefined,
                          });
                          setTransitionReason(""); setResolutionSummary("");
                          return d;
                        })}>
                        {STATUS_LABELS[s] ?? s}
                      </Btn>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            <Card>
              <h3 style={sectionTitle}>Merge duplicate</h3>
              <p style={{ margin: "0 0 8px", fontSize: 11, color: "var(--text-tertiary)" }}>
                Closes this request with a pointer into the target. History is never deleted.
                Both requests must belong to the same tenant.
              </p>
              <div style={{ display: "grid", gap: 8 }}>
                <input value={mergeId} onChange={e => setMergeId(e.target.value)}
                  placeholder="Target request ID (UUID)" style={inp} />
                <input value={mergeReason} onChange={e => setMergeReason(e.target.value)}
                  placeholder="Reason (required, min 3 chars)" style={inp} />
                <Btn size="sm" variant="danger" loading={busy}
                  disabled={!mergeId.trim() || mergeReason.trim().length < 3}
                  onClick={() => void run(async () => {
                    const d = await supportAdminApi.merge(t.id, { merge_into_id: mergeId.trim(), reason: mergeReason });
                    setMergeId(""); setMergeReason("");
                    return d;
                  })}>Merge into target</Btn>
              </div>
            </Card>

            {t.resolution_summary && (
              <Card>
                <h3 style={sectionTitle}>Resolution</h3>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>
                  {t.resolution_summary}
                </p>
                <p style={{ margin: "6px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
                  Resolved {fmt(t.resolved_at)} · reopened {t.reopen_count} time(s)
                </p>
              </Card>
            )}
          </div>
        </div>
      </PageShell>
    </AdminLayout>
  );
}
