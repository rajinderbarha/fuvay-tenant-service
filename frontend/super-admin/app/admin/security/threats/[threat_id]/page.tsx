"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, Ban, CheckCircle2, Clock3, Fingerprint, Network, ShieldAlert, UserX } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Badge, Btn, Modal, Select, Textarea } from "../../../../../components/shared/ui";
import { PageHeader, Skeleton } from "@serviceos/design-system";
import { platformUsersApi, securityAdminApi } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { usePermissions } from "../../../../../hooks/usePermissions";
import styles from "./threat.module.css";

const LEVEL_VARIANT: Record<string, "danger" | "warning" | "info" | "muted"> = { critical: "danger", high: "warning", medium: "info", low: "muted" };
type Action = "investigating" | "resolved" | "false_positive" | "block_ip" | "revoke_sessions";
function fmt(value?: string | null) { return value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "Not recorded"; }

export default function ThreatDetailPage() {
  const params = useParams(); const router = useRouter(); const permissions = usePermissions();
  const threatId = String(params.threat_id); const [pending, setPending] = useState<Action | null>(null); const [reason, setReason] = useState(""); const [assignee, setAssignee] = useState("");
  const threat = useApi(useCallback(() => securityAdminApi.getThreatDetail(threatId), [threatId]), [threatId]);
  const admins = useApi(useCallback(() => platformUsersApi.list({ user_group: "platform", status: "active", limit: 100 }), []), []);
  const statusAction = useAction(useCallback((payload: { status: string; reason: string }) => securityAdminApi.updateThreatStatus(threatId, payload.status, payload.reason), [threatId]));
  const blockAction = useAction(useCallback((value: string) => securityAdminApi.blockIpFromThreat(threatId, value), [threatId]));
  const revokeAction = useAction(useCallback((value: string) => securityAdminApi.revokeSessionsFromThreat(threatId, value), [threatId]));
  const assignAction = useAction(useCallback((adminId: string) => securityAdminApi.assignThreat(threatId, adminId), [threatId]));
  const t = threat.data;
  function request(action: Action) { setPending(action); setReason(""); }
  async function confirm() {
    if (!pending) return;
    const result = pending === "block_ip" ? await blockAction.execute(reason) : pending === "revoke_sessions" ? await revokeAction.execute(reason) : await statusAction.execute({ status: pending, reason });
    if (result) { setPending(null); setReason(""); threat.refetch(); }
  }
  async function assign() { const result = await assignAction.execute(assignee); if (result) { setAssignee(""); threat.refetch(); } }
  const loading = statusAction.loading || blockAction.loading || revokeAction.loading; const error = statusAction.error || blockAction.error || revokeAction.error;
  const actionCopy: Record<Action, { title: string; description: string; label: string; danger?: boolean }> = {
    investigating: { title: "Start investigation", description: "Moves this signal into the active investigation queue.", label: "Start investigation" },
    resolved: { title: "Resolve threat", description: "Closes the threat while retaining the complete evidence trail.", label: "Resolve threat" },
    false_positive: { title: "Mark false positive", description: "Closes the signal as benign. Explain the evidence behind this decision.", label: "Mark false positive" },
    block_ip: { title: "Block source network", description: "Immediately blocks requests from the detected IP for 30 days.", label: "Block IP", danger: true },
    revoke_sessions: { title: "Revoke user sessions", description: "Immediately signs the affected user out from every active device.", label: "Revoke sessions", danger: true },
  };
  return <AdminLayout activeNav="security"><main className={styles.page}>
    <PageHeader eyebrow="Security operations" context="Investigation" title={t ? `Threat ${t.threat_number ?? t.threat_id.slice(0, 8)}` : "Threat investigation"} description={t ? t.activity_type.replace(/_/g, " ") : "Loading evidence and response controls..."} actions={<><Btn variant="ghost" size="sm" icon={<ArrowLeft size={15} />} onClick={() => router.push("/admin/security?tab=threats")}>Threat queue</Btn>{t && <div className={styles.headerBadges}><Badge variant={LEVEL_VARIANT[t.threat_level] ?? "muted"}>{t.threat_level}</Badge><Badge variant={t.status === "open" ? "danger" : t.status === "resolved" ? "success" : "warning"}>{t.status.replace(/_/g, " ")}</Badge></div>}</>} />
    {threat.loading ? <Skeleton height={560} /> : !t ? <section className={styles.error}><AlertTriangle size={24} /><strong>Threat could not be loaded</strong><span>{threat.error}</span></section> : <>
      <section className={styles.hero}><div className={styles.risk}><ShieldAlert size={25} /><div><span>Risk score</span><strong>{t.risk_score}<small>/100</small></strong></div></div><div className={styles.description}><span>Detection summary</span><h2>{t.description}</h2><p>Detected {fmt(t.created_at)} · Last observed {fmt(t.last_seen_at)}</p></div><div className={styles.owner}><span>Response owner</span><strong>{t.assigned_to_admin_id ? "Assigned administrator" : "Unassigned"}</strong><small>{t.assigned_to_admin_id ?? "Claim from the threat queue"}</small></div></section>
      <div className={styles.workspace}><div className={styles.mainColumn}>
        <section className={styles.card}><header><h2>Evidence</h2><span>Immutable detection context</span></header><div className={styles.factGrid}><Fact icon={<Network size={16} />} label="Source IP" value={t.ip_address ?? "Not captured"} mono /><Fact icon={<Fingerprint size={16} />} label="Source engine" value={t.source ?? "Platform detection"} /><Fact icon={<ShieldAlert size={16} />} label="Detection rule" value={t.activity_type.replace(/_/g, " ")} /><Fact icon={<Clock3 size={16} />} label="Observed" value={`${t.detected_value ?? "—"} / threshold ${t.threshold ?? "—"}`} /><Fact label="Entity type" value={t.entity_type ?? "Not linked"} /><Fact label="Entity ID" value={t.entity_id ?? "Not linked"} mono /><Fact label="Target user" value={t.target_user_id ?? "Not linked"} mono /><Fact label="Resolution time" value={fmt(t.resolved_at)} /></div>{t.context && Object.keys(t.context).length > 0 && <details className={styles.context}><summary>View technical context</summary><pre>{JSON.stringify(t.context, null, 2)}</pre></details>}</section>
        <section className={styles.card}><header><h2>Response history</h2><span>{t.actions_taken?.length ?? 0} recorded actions</span></header><div className={styles.timeline}>{(t.actions_taken ?? []).length === 0 ? <div className={styles.empty}><CheckCircle2 size={20} /><span>No response action has been recorded.</span></div> : t.actions_taken!.map(a => <article key={a.log_id}><span /><div><strong>{a.operation.replace(/\./g, " · ").replace(/_/g, " ")}</strong><small>{a.actor_role ?? "System"} · {fmt(a.created_at)}</small></div></article>)}</div></section>
      </div><aside className={styles.sideColumn}><section className={styles.card}><header><h2>Response controls</h2><span>Reason required</span></header><div className={styles.actions}>{permissions.has("security:threats:update") && <div className={styles.assignment}><Select value={assignee} onChange={setAssignee} options={[{ value: "", label: "Assign investigator" }, ...(admins.data?.users ?? []).map(a => ({ value: a.id, label: `${a.full_name} · ${a.platform_role ?? a.role}` }))]} /><Btn variant="secondary" loading={assignAction.loading} disabled={!assignee} onClick={assign}>Assign</Btn>{assignAction.error && <small>{assignAction.error}</small>}</div>}{permissions.has("security:threats:resolve") && <><Btn onClick={() => request("investigating")} disabled={t.status === "investigating"}>Start investigation</Btn><Btn variant="secondary" onClick={() => request("resolved")} disabled={t.status === "resolved"}>Resolve threat</Btn><Btn variant="ghost" onClick={() => request("false_positive")}>Mark false positive</Btn></>}{permissions.has("security:threats:block_ip") && <Btn variant="danger" icon={<Ban size={14} />} onClick={() => request("block_ip")} disabled={!t.ip_address}>Block source IP</Btn>}{permissions.has("security:sessions:revoke") && <Btn variant="danger" icon={<UserX size={14} />} onClick={() => request("revoke_sessions")} disabled={!t.target_user_id}>Revoke user sessions</Btn>}</div></section><section className={styles.guidance}><ShieldAlert size={18} /><div><strong>Response guidance</strong><p>Validate the source and affected identity before containment. All actions are permanently recorded.</p></div></section></aside></div>
    </>}
    <Modal open={!!pending} onClose={() => setPending(null)} title={pending ? actionCopy[pending].title : "Confirm action"}><div className={styles.modal}><p>{pending ? actionCopy[pending].description : ""}</p><Textarea label="Decision reason" value={reason} onChange={setReason} rows={3} placeholder="Document the evidence and operational reason" required />{error && <div className={styles.modalError}>{error}</div>}<div><Btn variant="ghost" onClick={() => setPending(null)}>Cancel</Btn><Btn variant={pending && actionCopy[pending].danger ? "danger" : "primary"} loading={loading} disabled={reason.trim().length < 5} onClick={confirm}>{pending ? actionCopy[pending].label : "Confirm"}</Btn></div></div></Modal>
  </main></AdminLayout>;
}

function Fact({ icon, label, value, mono = false }: { icon?: React.ReactNode; label: string; value: string; mono?: boolean }) { return <div className={styles.fact}>{icon && <span>{icon}</span>}<div><small>{label}</small><strong className={mono ? styles.mono : undefined}>{value}</strong></div></div>; }
