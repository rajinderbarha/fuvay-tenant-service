"use client";
/**
 * Security & Threats — Enterprise SOC (7 tabs).
 * PROVEN: every mutating action (block IP, revoke session, create/rotate/revoke API key,
 * resolve threat) is backed by an audit-logged endpoint under /v1/admin/security/*.
 * Raw API keys are shown exactly once, in a dedicated modal, never persisted client-side.
 */
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw, Download, Ban, Shield, Key, UserCheck, ScrollText, SlidersHorizontal, AlertTriangle,
} from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Modal, Input, Skeleton } from "../../../components/shared/ui";
import { SummaryCardsRow } from "../../../components/pricing/SummaryCard";
import { ActionMenu } from "../../../components/pricing/ActionMenu";
import {
  securityAdminApi, SecurityThreat, SecuritySession, IPBlockEntry, SecurityApiKey, SecurityAuditEntry,
} from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { usePermissions } from "../../../hooks/usePermissions";
import { RequirePermission } from "../../../components/shared/PermissionGate";

type Tab = "overview" | "threats" | "sessions" | "ip_blocklist" | "api_keys" | "audit_logs" | "policies";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "overview", label: "Overview", icon: <Shield size={14} /> },
  { key: "threats", label: "Threats", icon: <AlertTriangle size={14} /> },
  { key: "sessions", label: "Active Sessions", icon: <UserCheck size={14} /> },
  { key: "ip_blocklist", label: "IP Blocklist", icon: <Ban size={14} /> },
  { key: "api_keys", label: "API Keys", icon: <Key size={14} /> },
  { key: "audit_logs", label: "Audit Logs", icon: <ScrollText size={14} /> },
  { key: "policies", label: "Security Policies", icon: <SlidersHorizontal size={14} /> },
];

const LEVEL_VARIANT: Record<string, "danger" | "warning" | "info" | "muted"> = {
  critical: "danger", high: "warning", medium: "info", low: "muted",
};

function EmptyState({ text }: { text: string }) {
  return <p style={{ padding: "28px 0", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>{text}</p>;
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>{children}</th>;
}
function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: "10px 12px", fontSize: 13, borderBottom: "1px solid var(--border)" }}>{children}</td>;
}

export default function SecurityPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <AdminLayout activeNav="security">
      <RequirePermission requiredPermission="security:read" parentLabel="Dashboard">
      <SectionHeader
        title="Security & Threats"
        subtitle="Threats, active sessions, IP blocklist, API keys, audit trail, and security policies."
      />
      <div style={{ padding: "0 28px 32px" }}>
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto" }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              display: "flex", alignItems: "center", gap: 6, padding: "10px 16px", border: "none",
              background: "none", cursor: "pointer", fontSize: 13, fontWeight: tab === t.key ? 700 : 500,
              color: tab === t.key ? "var(--accent)" : "var(--text-secondary)",
              borderBottom: tab === t.key ? "2px solid var(--accent)" : "2px solid transparent",
              whiteSpace: "nowrap",
            }}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {tab === "overview" && <OverviewTab />}
        {tab === "threats" && <ThreatsTab router={router} />}
        {tab === "sessions" && <SessionsTab />}
        {tab === "ip_blocklist" && <IpBlocklistTab />}
        {tab === "api_keys" && <ApiKeysTab />}
        {tab === "audit_logs" && <AuditLogsTab />}
        {tab === "policies" && <PoliciesTab />}
      </div>
      </RequirePermission>
    </AdminLayout>
  );
}

// ═══════════════════════════════════════════════════════════════
// OVERVIEW
// ═══════════════════════════════════════════════════════════════

function OverviewTab() {
  const overview = useApi(useCallback(() => securityAdminApi.getOverview(), []));
  const o = overview.data;

  if (overview.loading) return <Skeleton height={300} />;
  if (overview.error || !o) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Could not load overview. {overview.error}</p></Card>;

  const c = o.summary_cards;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <SummaryCardsRow cards={[
        { label: "Open Threats", value: c.open_threats, accent: c.open_threats > 0 },
        { label: "Critical Threats", value: c.critical_threats, accent: c.critical_threats > 0 },
        { label: "Active Sessions", value: c.active_sessions },
        { label: "Blocked IPs", value: c.blocked_ips },
        { label: "Active API Keys", value: c.active_api_keys },
        { label: "Expiring API Keys (30d)", value: c.expiring_api_keys, accent: c.expiring_api_keys > 0 },
        { label: "Failed Logins (24h)", value: c.failed_logins_24h },
        { label: "High-Risk Audit Events (24h)", value: c.high_risk_audit_events_24h },
      ]} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card padding={16}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Recent Threats</h3>
          {o.recent_threats.length === 0 ? <EmptyState text="No open threats." /> : o.recent_threats.map(t => (
            <div key={t.threat_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <Badge variant={LEVEL_VARIANT[t.threat_level] ?? "muted"} size="sm">{t.threat_level}</Badge>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 12.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.description}</p>
                <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{t.ip_address ?? "—"} · {new Date(t.created_at).toLocaleString("en-IN")}</p>
              </div>
            </div>
          ))}
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Recent High-Risk Audit Events</h3>
          {o.recent_high_risk_audit.length === 0 ? <EmptyState text="No high-risk actions recorded." /> : o.recent_high_risk_audit.map(a => (
            <div key={a.log_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <Badge variant="danger" size="sm">HIGH RISK</Badge>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 12.5 }}>{a.operation} · {a.engine_id}</p>
                <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{a.actor_role ?? "—"} · {a.actor_ip ?? "—"} · {new Date(a.created_at).toLocaleString("en-IN")}</p>
              </div>
            </div>
          ))}
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Top Blocked IPs</h3>
          {o.top_blocked_ips.length === 0 ? <EmptyState text="No active IP blocks." /> : o.top_blocked_ips.map(e => (
            <div key={e.entry_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
              <code style={{ fontSize: 12, background: "var(--surface-sunken)", padding: "2px 8px", borderRadius: 6 }}>{e.ip_or_cidr}</code>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)", flex: 1 }}>{e.reason}</span>
              <Badge variant={LEVEL_VARIANT[e.threat_level] ?? "muted"} size="sm">{e.hit_count} hits</Badge>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// THREATS
// ═══════════════════════════════════════════════════════════════

function ThreatsTab({ router }: { router: ReturnType<typeof useRouter> }) {
  const [status, setStatus] = useState("");
  const threats = useApi(useCallback(() => securityAdminApi.listThreats({ status: status || undefined, limit: 100 }), [status]));
  const statusAction = useAction(useCallback((id: string, s: string) => securityAdminApi.updateThreatStatus(id, s), []));
  const blockAction = useAction(useCallback((id: string, reason: string) => securityAdminApi.blockIpFromThreat(id, reason), []));
  const revokeAction = useAction(useCallback((id: string, reason: string) => securityAdminApi.revokeSessionsFromThreat(id, reason), []));

  async function act(t: SecurityThreat, fn: () => Promise<unknown>) {
    await fn();
    threats.refetch();
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        {["", "open", "investigating", "contained", "resolved", "false_positive", "ignored"].map(s => (
          <Btn key={s || "all"} size="sm" variant={status === s ? "primary" : "secondary"} onClick={() => setStatus(s)}>
            {s || "All"}
          </Btn>
        ))}
      </div>
      <Card padding={0}>
        {threats.loading ? <Skeleton height={200} /> : (threats.data?.threats.length ?? 0) === 0 ? <EmptyState text="No threats match this filter." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Threat #</Th><Th>Type</Th><Th>Level</Th><Th>Risk</Th><Th>IP</Th><Th>Status</Th><Th>Detected</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {threats.data!.threats.map(t => (
                <tr key={t.threat_id} style={{ cursor: "pointer" }} onClick={() => router.push(`/admin/security/threats/${t.threat_id}`)}>
                  <Td>{t.threat_number ?? t.threat_id.slice(0, 8)}</Td>
                  <Td>{t.activity_type.replace(/_/g, " ")}</Td>
                  <Td><Badge variant={LEVEL_VARIANT[t.threat_level] ?? "muted"} size="sm">{t.threat_level}</Badge></Td>
                  <Td>{t.risk_score}</Td>
                  <Td>{t.ip_address ?? "—"}</Td>
                  <Td><Badge variant={t.status === "open" ? "danger" : t.status === "resolved" ? "success" : "muted"} size="sm">{t.status}</Badge></Td>
                  <Td>{new Date(t.created_at).toLocaleString("en-IN")}</Td>
                  <Td>
                    <ActionMenu items={[
                      { label: "Mark Investigating", onClick: () => act(t, () => statusAction.execute(t.threat_id, "investigating")) },
                      { label: "Block IP", onClick: () => act(t, () => blockAction.execute(t.threat_id, "Blocked from threat review")), disabled: !t.ip_address },
                      { label: "Revoke Sessions", onClick: () => act(t, () => revokeAction.execute(t.threat_id, "Sessions revoked from threat review")), disabled: !t.target_user_id },
                      { label: "Mark Resolved", onClick: () => act(t, () => statusAction.execute(t.threat_id, "resolved")) },
                      { label: "Mark False Positive", onClick: () => act(t, () => statusAction.execute(t.threat_id, "false_positive")) },
                    ]} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ACTIVE SESSIONS
// ═══════════════════════════════════════════════════════════════

function SessionsTab() {
  const perm = usePermissions();
  const [q, setQ] = useState("");
  const sessions = useApi(useCallback(() => securityAdminApi.listSessions({ q: q || undefined, limit: 100 }), [q]));
  const revokeAction = useAction(useCallback((id: string, reason: string) => securityAdminApi.revokeSession(id, reason), []));
  const revokeAllAction = useAction(useCallback((userId: string, reason: string) => securityAdminApi.revokeAllUserSessions(userId, reason), []));

  async function revoke(s: SecuritySession) {
    await revokeAction.execute(s.session_id, "Revoked by admin from Active Sessions");
    sessions.refetch();
  }
  async function revokeAll(s: SecuritySession) {
    await revokeAllAction.execute(s.user_id, "All sessions revoked by admin");
    sessions.refetch();
  }

  return (
    <div>
      <div style={{ marginBottom: 14, maxWidth: 320 }}>
        <Input placeholder="Search by user, email, or IP..." value={q} onChange={setQ} />
      </div>
      <Card padding={0}>
        {sessions.loading ? <Skeleton height={200} /> : (sessions.data?.sessions.length ?? 0) === 0 ? <EmptyState text="No active sessions." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>User</Th><Th>Role</Th><Th>Device</Th><Th>IP</Th><Th>Status</Th><Th>Last Active</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {sessions.data!.sessions.map(s => (
                <tr key={s.session_id}>
                  <Td>{s.user_email}</Td>
                  <Td>{s.user_role}</Td>
                  <Td>{s.device_name}</Td>
                  <Td>{s.ip_address ?? "—"}</Td>
                  <Td><Badge variant={s.status === "active" ? "success" : "muted"} size="sm">{s.status}</Badge></Td>
                  <Td>{s.last_active_at ? new Date(s.last_active_at).toLocaleString("en-IN") : "—"}</Td>
                  <Td>
                    {perm.has("security:sessions:revoke") && (
                      <ActionMenu items={[
                        { label: "Revoke Session", onClick: () => revoke(s), disabled: s.status !== "active", destructive: true },
                        { label: "Revoke All Sessions", onClick: () => revokeAll(s), destructive: true },
                      ]} />
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// IP BLOCKLIST
// ═══════════════════════════════════════════════════════════════

function IpBlocklistTab() {
  const [modal, setModal] = useState(false);
  const [ip, setIp] = useState("");
  const [reason, setReason] = useState("");
  const blocklist = useApi(useCallback(() => securityAdminApi.listIpBlocklist({ limit: 100 }), []));
  const createAction = useAction(useCallback((ip: string, reason: string) => securityAdminApi.createIpBlock({ ipOrCidr: ip, reason }), []));
  const revokeAction = useAction(useCallback((id: string, reason: string) => securityAdminApi.revokeIpBlock(id, reason), []));

  async function handleCreate() {
    const r = await createAction.execute(ip, reason);
    if (r) { setModal(false); setIp(""); setReason(""); blocklist.refetch(); }
  }
  async function handleRevoke(e: IPBlockEntry) {
    await revokeAction.execute(e.entry_id, "Unblocked by admin");
    blocklist.refetch();
  }

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <Btn variant="danger" size="sm" icon={<Ban size={14} />} onClick={() => setModal(true)}>Block IP</Btn>
      </div>
      <Card padding={0}>
        {blocklist.loading ? <Skeleton height={200} /> : (blocklist.data?.entries.length ?? 0) === 0 ? <EmptyState text="No IP blocks configured." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>IP / CIDR</Th><Th>Reason</Th><Th>Level</Th><Th>Scope</Th><Th>Status</Th><Th>Hits</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {blocklist.data!.entries.map(e => (
                <tr key={e.entry_id}>
                  <Td><code>{e.ip_or_cidr}</code></Td>
                  <Td>{e.reason}</Td>
                  <Td><Badge variant={LEVEL_VARIANT[e.threat_level] ?? "muted"} size="sm">{e.threat_level}</Badge></Td>
                  <Td>{e.scope}</Td>
                  <Td><Badge variant={e.status === "active" ? "danger" : "muted"} size="sm">{e.status}</Badge></Td>
                  <Td>{e.hit_count}</Td>
                  <Td>
                    <ActionMenu items={[
                      { label: "Revoke Block", onClick: () => handleRevoke(e), disabled: e.status !== "active", destructive: true },
                    ]} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modal} onClose={() => setModal(false)} title="Block IP Address">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {createAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createAction.error}</p>}
          <Input label="IP Address or CIDR" placeholder="103.21.45.67 or 103.0.0.0/8" value={ip} onChange={setIp} required />
          <Input label="Reason" placeholder="Brute force attack, suspicious activity..." value={reason} onChange={setReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal(false)}>Cancel</Btn>
            <Btn variant="danger" size="sm" loading={createAction.loading} onClick={handleCreate}>Block IP</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// API KEYS
// ═══════════════════════════════════════════════════════════════

function ApiKeysTab() {
  const [modal, setModal] = useState(false);
  const [name, setName] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const keys = useApi(useCallback(() => securityAdminApi.listApiKeys({ limit: 100 }), []));
  const createAction = useAction(useCallback(
    (tenantId: string, name: string) => securityAdminApi.createApiKey({ tenantId, name, scopes: ["read:jobs"] }), []));
  const revokeAction = useAction(useCallback((keyId: string, tenantId: string, reason: string) => securityAdminApi.revokeApiKey(keyId, tenantId, reason), []));
  const rotateAction = useAction(useCallback((keyId: string, tenantId: string) => securityAdminApi.rotateApiKey(keyId, tenantId), []));

  async function handleCreate() {
    const r = await createAction.execute(tenantId, name);
    if (r) { setModal(false); setName(""); setTenantId(""); setRevealedKey(r.raw_key); keys.refetch(); }
  }
  async function handleRevoke(k: SecurityApiKey) {
    if (!k.tenant_id) return;
    await revokeAction.execute(k.key_id, k.tenant_id, "Revoked by admin");
    keys.refetch();
  }
  async function handleRotate(k: SecurityApiKey) {
    if (!k.tenant_id) return;
    const r = await rotateAction.execute(k.key_id, k.tenant_id);
    if (r) setRevealedKey(r.raw_key);
    keys.refetch();
  }

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <Btn variant="primary" size="sm" icon={<Key size={14} />} onClick={() => setModal(true)}>Create API Key</Btn>
      </div>
      <Card padding={0}>
        {keys.loading ? <Skeleton height={200} /> : (keys.data?.api_keys.length ?? 0) === 0 ? <EmptyState text="No API keys created yet." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Name</Th><Th>Prefix</Th><Th>Environment</Th><Th>Status</Th><Th>Uses</Th><Th>Created</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {keys.data!.api_keys.map(k => (
                <tr key={k.key_id}>
                  <Td>{k.name}</Td>
                  <Td><code>{k.key_prefix}</code></Td>
                  <Td>{k.environment}</Td>
                  <Td><Badge variant={k.status === "active" ? "success" : "muted"} size="sm">{k.status}</Badge></Td>
                  <Td>{k.use_count}</Td>
                  <Td>{new Date(k.created_at).toLocaleDateString("en-IN")}</Td>
                  <Td>
                    <ActionMenu items={[
                      { label: "Rotate Key", onClick: () => handleRotate(k), disabled: k.status !== "active" },
                      { label: "Revoke Key", onClick: () => handleRevoke(k), disabled: k.status !== "active", destructive: true },
                    ]} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modal} onClose={() => setModal(false)} title="Create API Key">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {createAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{createAction.error}</p>}
          <Input label="Tenant ID" value={tenantId} onChange={setTenantId} required />
          <Input label="Key Name" placeholder="e.g. Zapier Integration" value={name} onChange={setName} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading} onClick={handleCreate}>Create Key</Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!revealedKey} onClose={() => setRevealedKey(null)} title="API Key Created">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <p style={{ fontSize: 13, color: "var(--danger-text)", margin: 0, fontWeight: 600 }}>
            This key will not be shown again. Copy it now and store it securely.
          </p>
          <code style={{ display: "block", padding: "12px 14px", background: "var(--surface-sunken)", borderRadius: 8, fontSize: 12, wordBreak: "break-all" }}>
            {revealedKey}
          </code>
          <Btn variant="secondary" size="sm" onClick={() => { if (revealedKey) navigator.clipboard.writeText(revealedKey); }}>
            Copy to clipboard
          </Btn>
        </div>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// AUDIT LOGS
// ═══════════════════════════════════════════════════════════════

function AuditLogsTab() {
  const [q, setQ] = useState("");
  const logs = useApi(useCallback(() => securityAdminApi.listAuditLogs({ q: q || undefined, limit: 100 }), [q]));
  const exportAction = useAction(useCallback(() => securityAdminApi.exportAuditLogs(), []));

  async function handleExport() {
    const blob = await exportAction.execute();
    if (blob) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "security_audit_log.csv"; a.click();
      URL.revokeObjectURL(url);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "center" }}>
        <div style={{ maxWidth: 320, flex: 1 }}>
          <Input placeholder="Search by operation, entity, or IP..." value={q} onChange={setQ} />
        </div>
        <Btn variant="secondary" size="sm" icon={<Download size={14} />} loading={exportAction.loading} onClick={handleExport}>
          Export Audit Log
        </Btn>
      </div>
      <Card padding={0}>
        {logs.loading ? <Skeleton height={200} /> : (logs.data?.audit_logs.length ?? 0) === 0 ? <EmptyState text="No audit entries match this filter." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Operation</Th><Th>Engine</Th><Th>Actor Role</Th><Th>IP</Th><Th>Risk</Th><Th>When</Th></tr></thead>
            <tbody>
              {logs.data!.audit_logs.map((l: SecurityAuditEntry) => (
                <tr key={l.log_id}>
                  <Td>{l.operation}</Td>
                  <Td>{l.engine_id}</Td>
                  <Td>{l.actor_role ?? "—"}</Td>
                  <Td>{l.actor_ip ?? "—"}</Td>
                  <Td><Badge variant={l.is_high_risk ? "danger" : "muted"} size="sm">{l.is_high_risk ? "HIGH RISK" : "normal"}</Badge></Td>
                  <Td>{new Date(l.created_at).toLocaleString("en-IN")}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p style={{ padding: "10px 12px", margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
          Audit log is append-only. No entries can be modified or deleted.
        </p>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SECURITY POLICIES
// ═══════════════════════════════════════════════════════════════

function PoliciesTab() {
  const policies = useApi(useCallback(() => securityAdminApi.getPolicies(), []));
  const updateAction = useAction(useCallback((key: string, value: unknown, reason: string) => securityAdminApi.updatePolicy(key, value, reason), []));
  const [editKey, setEditKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editReason, setEditReason] = useState("");

  function openEdit(policyKey: string, currentValue: unknown) {
    setEditKey(policyKey);
    setEditValue(typeof currentValue === "object" ? JSON.stringify(currentValue) : String(currentValue));
    setEditReason("");
  }

  async function handleSave() {
    if (!editKey) return;
    let parsed: unknown = editValue;
    if (editValue === "true") parsed = true;
    else if (editValue === "false") parsed = false;
    else if (!isNaN(Number(editValue)) && editValue.trim() !== "") parsed = Number(editValue);
    const r = await updateAction.execute(editKey, parsed, editReason);
    if (r) { setEditKey(null); policies.refetch(); }
  }

  return (
    <div>
      <Card padding={0}>
        {policies.loading ? <Skeleton height={200} /> : (policies.data?.policies.length ?? 0) === 0 ? <EmptyState text="No security policies configured." /> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><Th>Policy</Th><Th>Value</Th><Th>Description</Th><Th>{" "}</Th></tr></thead>
            <tbody>
              {policies.data!.policies.map(p => (
                <tr key={p.id}>
                  <Td><code>{p.policy_key}</code></Td>
                  <Td>{typeof p.policy_value === "object" ? JSON.stringify(p.policy_value) : String(p.policy_value)}</Td>
                  <Td>{p.description ?? "—"}</Td>
                  <Td><Btn variant="secondary" size="xs" onClick={() => openEdit(p.policy_key, p.policy_value)}>Edit</Btn></Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={!!editKey} onClose={() => setEditKey(null)} title={`Update Policy: ${editKey ?? ""}`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {updateAction.error && <p style={{ color: "var(--danger-text)", fontSize: 12 }}>{updateAction.error}</p>}
          <Input label="New Value" value={editValue} onChange={setEditValue} required />
          <Input label="Reason (required)" placeholder="Why is this policy changing?" value={editReason} onChange={setEditReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setEditKey(null)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={updateAction.loading} disabled={!editReason} onClick={handleSave}>Save</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
