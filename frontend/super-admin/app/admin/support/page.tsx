"use client";
import { TableSurface } from "@serviceos/design-system";
// SUPER-ADMIN TENANT SUPPORT QUEUE.
// The backend (app/engines/support/admin_router.py) was fully built and
// live-proven, but there was NO Super Admin page for it at all -- every admin
// action was only reachable via curl. This is that missing surface.
// All shapes come from app/engines/support/service.py ticket_row() and
// service_status(); nothing is reshaped or invented here.
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { Badge, Btn, Card, Skeleton, StatCard, EmptyState } from "../../../components/shared/ui";
import { ApiErrorState } from "../../../components/shared/ApiStates";
import {
  supportAdminApi, ServiceOSError,
  SupportQueueResponse, SupportIncidentRow, SupportServiceStatus,
} from "../../../lib/api";

const PRIORITY_VARIANT: Record<string, "muted" | "default" | "warning" | "danger" | "info"> = {
  low: "muted", normal: "default", high: "warning", urgent: "danger", critical: "danger",
};
const BREACH_VARIANT: Record<string, "success" | "warning" | "danger" | "muted" | "info"> = {
  on_track: "success", at_risk: "warning", breached: "danger",
  paused: "info", met: "success", not_applicable: "muted",
};

function fmt(ts: string | null | undefined) {
  return ts ? ts.replace("T", " ").slice(0, 16) : "—";
}

export default function AdminSupportQueuePage() {
  const router = useRouter();
  const [tab, setTab] = useState<"queue" | "status">("queue");

  const [data, setData] = useState<SupportQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<ServiceOSError | null>(null);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [assignee, setAssignee] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      setData(await supportAdminApi.queue({
        search: search || undefined, status: status || undefined,
        priority: priority || undefined, category: category || undefined,
        tenant_id: tenantId || undefined, limit: 100,
      }));
    } catch (e) {
      setErr(e as ServiceOSError);
    } finally { setLoading(false); }
  }, [search, status, priority, category, tenantId]);

  useEffect(() => { void load(); }, [load]);

  // Assignee is filtered client-side: the backend queue endpoint has no
  // assignee filter (checked route-by-route), so this narrows the fetched page
  // rather than pretending to be a server-side filter.
  const rows = (data?.items ?? []).filter(r =>
    !assignee || (r.assigned_admin_name ?? "").toLowerCase().includes(assignee.toLowerCase())
    || (r.assigned_team ?? "").toLowerCase().includes(assignee.toLowerCase()));

  const selStyle: React.CSSProperties = {
    height: 34, padding: "0 10px", borderRadius: 9, fontSize: 12,
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontFamily: "inherit",
  };

  return (
    <AdminLayout>
      <PageShell>
        <PageHeader
          title="Tenant Support"
          description="ServiceOS support queue — tenant businesses asking the platform for help. Customer service complaints live under Home Services → Complaints."
          actions={<Btn variant="secondary" size="sm" onClick={() => void load()}>Refresh</Btn>}
        />

        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)" }}>
          {([["queue", "Support queue"], ["status", "Platform status & incidents"]] as const).map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} style={{
              padding: "8px 16px", fontSize: 13, fontWeight: 600, borderRadius: "8px 8px 0 0",
              border: tab === id ? "1px solid var(--border)" : "1px solid transparent",
              borderBottom: tab === id ? "1px solid var(--surface)" : "1px solid transparent",
              marginBottom: tab === id ? -1 : 0,
              background: tab === id ? "var(--surface)" : "none",
              color: tab === id ? "var(--brand)" : "var(--text-tertiary)",
              cursor: "pointer", fontFamily: "inherit",
            }}>{label}</button>
          ))}
        </div>

        {tab === "status" ? <StatusPanel /> : (
          <>
            {data && (
              <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
                <StatCard label="Open"                value={data.counts.open} />
                <StatCard label="Unassigned"          value={data.counts.unassigned} />
                <StatCard label="Awaiting tenant"     value={data.counts.waiting_for_tenant} />
                <StatCard label="Resolved / closed"   value={data.counts.resolved} />
                <StatCard label="SLA breached (page)" value={data.counts.sla_breached_on_page}
                          alert={data.counts.sla_breached_on_page > 0} />
              </div>
            )}

            <Card padding={14}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <input value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search subject, ticket number, description…"
                  style={{ ...selStyle, minWidth: 260, flex: 1 }} />
                <select value={status} onChange={e => setStatus(e.target.value)} style={selStyle}>
                  <option value="">All statuses</option>
                  <option value="open">Open (any)</option>
                  {(data?.statuses ?? []).map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <select value={priority} onChange={e => setPriority(e.target.value)} style={selStyle}>
                  <option value="">All priorities</option>
                  {(data?.priorities ?? []).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <select value={category} onChange={e => setCategory(e.target.value)} style={selStyle}>
                  <option value="">All categories</option>
                  {(data?.categories ?? []).map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
                </select>
                <input value={tenantId} onChange={e => setTenantId(e.target.value)}
                  placeholder="Tenant ID" style={{ ...selStyle, width: 200 }} />
                <input value={assignee} onChange={e => setAssignee(e.target.value)}
                  placeholder="Assignee / team" style={{ ...selStyle, width: 160 }} />
              </div>
            </Card>

            {err ? <ApiErrorState error={err} onRetry={() => void load()} />
              : loading ? (
                <Card><div style={{ display: "grid", gap: 10 }}>
                  {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} height={34} />)}
                </div></Card>
              ) : rows.length === 0 ? (
                <Card><EmptyState title="No support requests match these filters."
                  description="Tenants raise these from their Help & Support workspace." /></Card>
              ) : (
                <Card padding={0} style={{ overflowX: "auto" }}>
                  <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "var(--surface-sunken)", textAlign: "left" }}>
                        {["Request", "Tenant", "Category", "Priority", "Status", "SLA", "Assignee", "Updated"].map(h => (
                          <th key={h} style={{ padding: "10px 12px", fontSize: 11, fontWeight: 700,
                            color: "var(--text-tertiary)", letterSpacing: "0.04em", textTransform: "uppercase",
                            borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(r => (
                        <tr key={r.id} onClick={() => router.push(`/admin/support/${r.id}`)}
                          style={{ cursor: "pointer", borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "10px 12px" }}>
                            <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{r.subject}</div>
                            <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                              {r.ticket_number}{r.is_critical_incident ? " · CRITICAL INCIDENT" : ""}
                            </div>
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 11, color: "var(--text-secondary)" }}>
                            <div>{r.reporter_name ?? "—"}</div>
                            <div style={{ color: "var(--text-tertiary)" }}>{r.tenant_id.slice(0, 8)}…</div>
                          </td>
                          <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{r.category_label}</td>
                          <td style={{ padding: "10px 12px" }}>
                            <Badge variant={PRIORITY_VARIANT[r.priority] ?? "default"} size="sm">{r.priority}</Badge>
                          </td>
                          <td style={{ padding: "10px 12px" }}>
                            <Badge variant="muted" size="sm">{r.status_label}</Badge>
                          </td>
                          <td style={{ padding: "10px 12px" }}>
                            <Badge variant={BREACH_VARIANT[r.sla_breach_state] ?? "muted"} size="sm" dot>
                              {r.sla_breach_state.replace(/_/g, " ")}
                            </Badge>
                            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{r.sla_display}</div>
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>
                            {r.assigned_admin_name ?? r.assigned_team ?? <span style={{ color: "var(--warning-text)" }}>Unassigned</span>}
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                            {fmt(r.updated_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </TableSurface>
                </Card>
              )}
            {data && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
              Showing {rows.length} of {data.total} matching support requests.
            </p>}
          </>
        )}
      </PageShell>
    </AdminLayout>
  );
}

// ── Platform status & incidents ─────────────────────────────────────────────
function StatusPanel() {
  const [incidents, setIncidents] = useState<SupportIncidentRow[]>([]);
  const [status, setStatus] = useState<SupportServiceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<ServiceOSError | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", severity: "minor", components: "" });
  const [component, setComponent] = useState("api");

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try { setIncidents((await supportAdminApi.listIncidents()).items); }
    catch (e) { setErr(e as ServiceOSError); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const beat = async (healthy: boolean) => {
    setBusy(true);
    try { setStatus(await supportAdminApi.heartbeat(component, healthy)); }
    catch (e) { setErr(e as ServiceOSError); }
    finally { setBusy(false); }
  };

  const create = async () => {
    if (form.title.trim().length < 3) return;
    setBusy(true);
    try {
      await supportAdminApi.createIncident({
        title: form.title, description: form.description || undefined,
        severity: form.severity,
        components: form.components ? form.components.split(",").map(s => s.trim()).filter(Boolean) : undefined,
      });
      setForm({ title: "", description: "", severity: "minor", components: "" });
      await load();
    } catch (e) { setErr(e as ServiceOSError); }
    finally { setBusy(false); }
  };

  const inp: React.CSSProperties = {
    height: 34, padding: "0 10px", borderRadius: 9, fontSize: 12, width: "100%",
    border: "1px solid var(--border)", background: "var(--surface)",
    color: "var(--text-primary)", fontFamily: "inherit",
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {err && <ApiErrorState error={err} onRetry={() => void load()} />}

      <Card>
        <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700 }}>Status heartbeat</h3>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--text-secondary)" }}>
          The tenant-facing status banner refuses to claim &ldquo;Operational&rdquo; without recent evidence.
          Posting a heartbeat here is currently the only mechanism that produces that evidence —
          there is no scheduled/automatic heartbeat job in the backend.
        </p>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input value={component} onChange={e => setComponent(e.target.value)}
            placeholder="component (e.g. api)" style={{ ...inp, width: 200 }} />
          <Btn size="sm" variant="success" loading={busy} onClick={() => void beat(true)}>Report healthy</Btn>
          <Btn size="sm" variant="warning" loading={busy} onClick={() => void beat(false)}>Report degraded</Btn>
        </div>
        {status && (
          <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-secondary)" }}>
            <Badge variant={status.state === "operational" ? "success" : status.state === "unavailable" ? "muted" : "warning"}>
              {status.state.replace(/_/g, " ")}
            </Badge>
            <span style={{ marginLeft: 8 }}>{status.message}</span>
            <span style={{ marginLeft: 8, color: "var(--text-tertiary)" }}>
              last checked {fmt(status.last_checked_at)}
            </span>
          </div>
        )}
      </Card>

      <Card>
        <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700 }}>Declare a platform incident</h3>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "2fr 1fr 1fr auto", alignItems: "center" }}>
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
            placeholder="Incident title" style={inp} />
          <select value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })} style={inp}>
            <option value="maintenance">maintenance</option>
            <option value="minor">minor</option>
            <option value="major">major</option>
          </select>
          <input value={form.components} onChange={e => setForm({ ...form, components: e.target.value })}
            placeholder="components (comma separated)" style={inp} />
          <Btn size="sm" loading={busy} disabled={form.title.trim().length < 3} onClick={() => void create()}>Declare</Btn>
        </div>
        <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
          placeholder="What tenants should know (optional)" rows={2}
          style={{ ...inp, height: "auto", padding: 10, marginTop: 8, resize: "vertical" }} />
      </Card>

      <Card padding={0}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", fontWeight: 700, fontSize: 14 }}>
          Incidents
        </div>
        {loading ? <div style={{ padding: 16 }}><Skeleton height={30} /></div>
          : incidents.length === 0 ? <div style={{ padding: 16, fontSize: 13, color: "var(--text-tertiary)" }}>
              No platform incidents recorded.</div>
          : (
            <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <tbody>
                {incidents.map(i => (
                  <tr key={i.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px" }}>
                      <div style={{ fontWeight: 600 }}>{i.title}</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                        {i.reference} · started {fmt(i.started_at)}
                        {i.components.length > 0 ? ` · ${i.components.join(", ")}` : ""}
                      </div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <Badge size="sm" variant={i.severity === "major" ? "danger" : i.severity === "minor" ? "warning" : "info"}>
                        {i.severity}
                      </Badge>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <Badge size="sm" variant={i.resolved_at ? "success" : "muted"}>{i.status}</Badge>
                    </td>
                    <td style={{ padding: "10px 16px", textAlign: "right" }}>
                      {!i.resolved_at && (
                        <Btn size="xs" variant="secondary" loading={busy} onClick={async () => {
                          setBusy(true);
                          try { await supportAdminApi.resolveIncident(i.id); await load(); }
                          catch (e) { setErr(e as ServiceOSError); }
                          finally { setBusy(false); }
                        }}>Resolve</Btn>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          )}
      </Card>
    </div>
  );
}
