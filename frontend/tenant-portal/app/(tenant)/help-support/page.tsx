"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Help & Support — the tenant↔ServiceOS platform support workspace.
 *
 * DOMAIN BOUNDARY: this page is for problems the PROVIDER BUSINESS has with
 * its ServiceOS account or the platform. A CUSTOMER disputing a service job
 * is a complaint and belongs to /home-services/complaints — this page links
 * there and never accepts job complaints. Backed by the TENANT-SUPPORT
 * engine (/v1/tenant/support/*, migration 207); the Super Admin support
 * queue reads the same tickets through /v1/admin/support/*.
 *
 * Everything shown here is backend-derived: priority (from the impact the
 * tenant chooses), SLA, allowed actions, assignment, service status and
 * knowledge-base content. No hardcoded article list, no fabricated status.
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search, RefreshCw, Plus, AlertTriangle, AlertCircle, CheckCircle2, Clock,
  ShieldAlert, Rocket, Wrench, Users, Tag, Wallet, Shield, ChevronRight,
  Megaphone, BookOpen, X, Paperclip, LifeBuoy, ArrowUpRight, Send, Activity,
} from "lucide-react";
import {
  supportApi, ServiceOSError,
  type SupportWorkspace, type SupportRequestRow, type SupportRequestDetail,
  type SupportServiceStatus, type SupportKnowledge, type SupportAnnouncementItem,
  type SupportArticle,
} from "../../../lib/api";
import { Skeleton, Btn, Badge, Card, Modal, Input, Select, EmptyState } from "../../../components/shared/ui";

type Tab = "requests" | "knowledge" | "announcements";
const TABS: { id: Tab; label: string }[] = [
  { id: "requests", label: "My Support Requests" },
  { id: "knowledge", label: "Knowledge Base" },
  { id: "announcements", label: "Announcements" },
];

const QUICK_HELP_ICONS: Record<string, React.ReactNode> = {
  rocket: <Rocket size={16} />, wrench: <Wrench size={16} />, users: <Users size={16} />,
  tag: <Tag size={16} />, wallet: <Wallet size={16} />, shield: <Shield size={16} />,
};

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  draft: "muted", submitted: "info", triaged: "info", assigned: "info",
  investigating: "info", waiting_for_tenant: "warning", waiting_for_serviceos: "info",
  resolved: "success", closed: "muted", reopened: "warning", withdrawn: "muted",
};

const PRIORITY_VARIANT: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  low: "muted", normal: "info", high: "warning", urgent: "danger", critical: "danger",
};

const SLA_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  on_track: "success", met: "success", at_risk: "warning", paused: "warning",
  breached: "danger", not_applicable: "muted",
};

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

const ROW_LABEL: React.CSSProperties = {
  fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600,
  textTransform: "uppercase", letterSpacing: "0.04em",
};
const TH: React.CSSProperties = {
  textAlign: "left", padding: "9px 12px", fontSize: 11, fontWeight: 700,
  color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em",
  borderBottom: "1px solid var(--border)", whiteSpace: "nowrap",
};
const TD: React.CSSProperties = {
  padding: "10px 12px", fontSize: 12.5, color: "var(--text-primary)",
  borderBottom: "1px solid var(--border-subtle, var(--border))", verticalAlign: "middle",
};

// ── Service status banner (never green without real evidence) ────────────────
function StatusBanner({ status }: { status: SupportServiceStatus }) {
  const cfg = {
    operational:    { variant: "success" as const, label: "Operational",       icon: <CheckCircle2 size={15} /> },
    degraded:       { variant: "warning" as const, label: "Degraded",          icon: <AlertTriangle size={15} /> },
    major_incident: { variant: "danger"  as const, label: "Major incident",    icon: <ShieldAlert size={15} /> },
    maintenance:    { variant: "info"    as const, label: "Maintenance",       icon: <Clock size={15} /> },
    unavailable:    { variant: "muted"   as const, label: "Status unavailable", icon: <AlertCircle size={15} /> },
  }[status.state];
  const tone = {
    success: "var(--success-bg)", warning: "var(--warning-bg)", danger: "var(--danger-bg)",
    info: "var(--info-bg)", muted: "var(--surface-sunken)",
  }[cfg.variant];
  const border = {
    success: "var(--success-border)", warning: "var(--warning-border)", danger: "var(--danger-border)",
    info: "var(--info-border)", muted: "var(--border)",
  }[cfg.variant];

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
      background: tone, border: `1px solid ${border}`, borderRadius: 10,
      padding: "10px 14px", marginBottom: 16,
    }}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
        {cfg.icon}
        <Badge variant={cfg.variant} size="sm" dot>{cfg.label}</Badge>
      </span>
      <span style={{ fontSize: 12.5, color: "var(--text-primary)", flex: 1, minWidth: 220 }}>
        {status.message}
      </span>
      {status.affected_components.length > 0 && (
        <span style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>
          Affected: {status.affected_components.join(", ")}
        </span>
      )}
      {status.active_incident_count > 0 && (
        <Badge variant="danger" size="sm">{status.active_incident_count} active incident{status.active_incident_count === 1 ? "" : "s"}</Badge>
      )}
      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        Last checked {status.last_checked_at ? fmt(status.last_checked_at) : "never"}
      </span>
      <Link href={status.status_page_href} style={{ fontSize: 12, fontWeight: 700, color: "var(--brand)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
        View service status <ArrowUpRight size={13} />
      </Link>
    </div>
  );
}

// ── Create support request (3 step guided flow) ──────────────────────────────
function CreateRequestDrawer({
  open, onClose, ws, onCreated,
}: {
  open: boolean; onClose: () => void; ws: SupportWorkspace;
  onCreated: (d: SupportRequestDetail) => void;
}) {
  const [step, setStep] = useState(1);
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [feature, setFeature] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [startedAt, setStartedAt] = useState("");
  const [impact, setImpact] = useState("");
  const [relatedKey, setRelatedKey] = useState("");
  const [relatedValue, setRelatedValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setStep(1); setErr(null);
    }
  }, [open]);

  const similar = useMemo(
    () => ws.requests.filter(r => r.category === category && !["resolved", "closed", "withdrawn"].includes(r.status)),
    [ws.requests, category],
  );

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const related: Record<string, string> = {};
      if (relatedKey && relatedValue.trim()) related[relatedKey] = relatedValue.trim();
      const d = await supportApi.createRequest({
        category, subject, description, impact,
        subcategory: subcategory || undefined,
        affected_feature: feature || undefined,
        started_at: startedAt ? new Date(startedAt).toISOString() : undefined,
        related_entities: Object.keys(related).length ? related : undefined,
      });
      onCreated(d);
      onClose();
    } catch (e) {
      // Never lose what was typed — the drawer stays open with all fields intact.
      setErr(e instanceof ServiceOSError ? e.message : "Could not submit your request. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const step1Ok = !!category;
  const step2Ok = subject.trim().length >= 3 && description.trim().length >= 10 && !!impact;

  return (
    <Modal open={open} onClose={onClose} title="Create support request" size="lg">
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {["What is affected", "Describe the problem", "Evidence & submit"].map((label, i) => (
          <div key={label} style={{
            flex: 1, padding: "7px 10px", borderRadius: 8, fontSize: 11.5, fontWeight: 700,
            background: step === i + 1 ? "var(--accent-muted)" : "var(--surface-sunken)",
            color: step === i + 1 ? "var(--accent)" : "var(--text-tertiary)",
            border: `1px solid ${step === i + 1 ? "var(--accent)" : "var(--border)"}`,
          }}>{i + 1}. {label}</div>
        ))}
      </div>

      {step === 1 && (
        <div style={{ display: "grid", gap: 12 }}>
          <Select label="Category" value={category} onChange={v => { setCategory(v); setSubcategory(""); }}
            placeholder="Choose the area this is about"
            options={ws.form_options.categories.map(c => ({ value: c.key, label: c.label }))} />
          {category && (ws.form_options.subcategories[category] || []).length > 0 && (
            <Select label="What best describes it? (optional)" value={subcategory} onChange={setSubcategory}
              placeholder="Choose a closer match"
              options={(ws.form_options.subcategories[category] || []).map(s => ({ value: s, label: s }))} />
          )}
          <Input label="Affected page or feature (optional)" value={feature} onChange={setFeature}
            placeholder="e.g. /home-services/dispatch" />
          <div style={{
            background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: 8,
            padding: "9px 12px", fontSize: 12, color: "var(--info-text)",
          }}>
            {ws.complaints_redirect.message}{" "}
            <Link href={ws.complaints_redirect.href} style={{ fontWeight: 700, color: "inherit" }}>Open Complaints</Link>
          </div>
        </div>
      )}

      {step === 2 && (
        <div style={{ display: "grid", gap: 12 }}>
          <Input label="Subject" value={subject} onChange={setSubject} required
            placeholder="One line describing the problem" />
          <Input label="What happened?" value={description} onChange={setDescription} rows={5} required
            placeholder="What you expected, what happened instead, and anything you already tried." />
          <Input label="When did it start? (optional)" value={startedAt} onChange={setStartedAt} type="datetime-local" />
          <Select label="Impact on your business" value={impact} onChange={setImpact}
            placeholder="How much is this blocking you?"
            options={ws.form_options.impacts.map(i => ({ value: i.key, label: i.label }))} />
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            ServiceOS sets the internal priority and response targets from your impact, the
            category and the affected capability — you never need to pick a priority.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <Select label="Link a record (optional)" value={relatedKey} onChange={setRelatedKey}
              placeholder="Reference type"
              options={ws.form_options.related_entity_keys.map(k => ({ value: k, label: k.replace(/_/g, " ") }))} />
            <Input label="Reference ID" value={relatedValue} onChange={setRelatedValue}
              placeholder="Paste the ID only" hint="Only the ID is stored — never customer details." />
          </div>
          {similar.length > 0 && (
            <div style={{
              background: "var(--warning-bg)", border: "1px solid var(--warning-border)",
              borderRadius: 8, padding: "9px 12px", fontSize: 12, color: "var(--warning-text)",
            }}>
              You already have {similar.length} open request{similar.length === 1 ? "" : "s"} in this
              category ({similar.slice(0, 2).map(s => s.ticket_number).join(", ")}). You can still submit
              this one if it is a different problem.
            </div>
          )}
        </div>
      )}

      {step === 3 && (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{
            background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
            borderRadius: 8, padding: "10px 12px", fontSize: 12, color: "var(--danger-text)",
            display: "flex", gap: 8,
          }}>
            <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{ws.form_options.attachment_privacy_warning}</span>
          </div>
          <div style={{
            border: "1px dashed var(--border)", borderRadius: 8, padding: 14,
            fontSize: 12, color: "var(--text-secondary)",
          }}>
            <Paperclip size={14} style={{ verticalAlign: -2, marginRight: 6 }} />
            You can attach screenshots or a PDF once the request is created — open the request and
            use <strong>Attach file</strong> in the conversation panel.
          </div>
          <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 12, fontSize: 12.5 }}>
            <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 6 }}>
              <span style={ROW_LABEL}>Category</span>
              <span>{ws.form_options.categories.find(c => c.key === category)?.label ?? "—"}</span>
              <span style={ROW_LABEL}>Subject</span>
              <span>{subject || "—"}</span>
              <span style={ROW_LABEL}>Impact</span>
              <span>{ws.form_options.impacts.find(i => i.key === impact)?.label ?? "—"}</span>
            </div>
          </div>
        </div>
      )}

      {err && (
        <div style={{
          marginTop: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          borderRadius: 8, padding: "9px 12px", fontSize: 12, color: "var(--danger-text)",
        }}>{err}</div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginTop: 18 }}>
        <Btn variant="ghost" onClick={() => (step === 1 ? onClose() : setStep(step - 1))}>
          {step === 1 ? "Cancel" : "Back"}
        </Btn>
        {step < 3
          ? <Btn onClick={() => setStep(step + 1)} disabled={step === 1 ? !step1Ok : !step2Ok}>Continue</Btn>
          : <Btn onClick={submit} loading={busy} disabled={busy || !step2Ok} icon={<Send size={14} />}>Submit request</Btn>}
      </div>
    </Modal>
  );
}

// ── Critical incident panel ─────────────────────────────────────────────────
function CriticalIncidentModal({
  open, onClose, ws, onCreated,
}: {
  open: boolean; onClose: () => void; ws: SupportWorkspace;
  onCreated: (d: SupportRequestDetail) => void;
}) {
  const [key, setKey] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      onCreated(await supportApi.reportCriticalIncident({
        critical_impact_key: key, subject, description,
      }));
      onClose();
    } catch (e) {
      setErr(e instanceof ServiceOSError ? e.message : "Could not report the incident.");
    } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Report a critical incident" size="md">
      <p style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 0 }}>
        Use this only when ServiceOS is unusable or your operations have stopped. It pages the
        ServiceOS incident response team directly and is rate-limited. Normal questions should
        go through a support request instead.
      </p>
      <div style={{ display: "grid", gap: 12 }}>
        <Select label="What is happening?" value={key} onChange={setKey}
          placeholder="Choose the incident type"
          options={ws.form_options.critical_impacts.map(c => ({ value: c.key, label: c.label }))} />
        <Input label="Subject" value={subject} onChange={setSubject} required
          placeholder="One line, e.g. no user can open the portal" />
        <Input label="What is affected right now?" value={description} onChange={setDescription} rows={4} required
          placeholder="Which users, since when, and what you see." />
      </div>
      {err && (
        <div style={{
          marginTop: 12, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          borderRadius: 8, padding: "9px 12px", fontSize: 12, color: "var(--danger-text)",
        }}>{err}</div>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
        <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        <Btn variant="danger" onClick={submit} loading={busy}
          disabled={busy || !key || subject.trim().length < 3 || description.trim().length < 10}>
          Report incident
        </Btn>
      </div>
    </Modal>
  );
}

// ── Request detail panel ────────────────────────────────────────────────────
function RequestDetailPanel({
  detail, loading, error, onRefresh, canReply,
}: {
  detail: SupportRequestDetail | null; loading: boolean; error: string | null;
  onRefresh: () => void; canReply: boolean;
}) {
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionErr, setActionErr] = useState<string | null>(null);

  useEffect(() => { setActionErr(null); }, [detail?.id]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setActionErr(null);
    try { await fn(); onRefresh(); }
    catch (e) { setActionErr(e instanceof ServiceOSError ? e.message : "That action could not be completed."); }
    finally { setBusy(false); }
  };

  const sendReply = async () => {
    if (!detail || !reply.trim()) return;
    setBusy(true); setActionErr(null);
    try {
      await supportApi.reply(detail.id, reply);
      setReply("");          // cleared only after a confirmed success
      onRefresh();
    } catch (e) {
      // Draft is deliberately retained so a failed send never loses typing.
      setActionErr(e instanceof ServiceOSError ? e.message : "Your reply was not sent. It is still here — try again.");
    } finally { setBusy(false); }
  };

  if (loading) {
    return <Card padding={16}><Skeleton height={22} width="60%" /><div style={{ height: 10 }} /><Skeleton height={140} /></Card>;
  }
  if (error) {
    return (
      <Card padding={16}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <AlertCircle size={16} color="var(--danger-text)" />
          <strong style={{ fontSize: 13 }}>Could not load this request</strong>
        </div>
        <p style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{error}</p>
        <Btn size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={onRefresh}>Retry</Btn>
      </Card>
    );
  }
  if (!detail) {
    return (
      <Card padding={20}>
        <EmptyState icon={<LifeBuoy size={26} />} title="Select a request"
          description="Choose a support request on the left to see its conversation, SLA and history." />
      </Card>
    );
  }

  const a = detail.allowed_actions;
  return (
    <Card padding={0} style={{ overflow: "hidden" }}>
      <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
          <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-tertiary)" }}>{detail.ticket_number}</span>
          <Badge variant={STATUS_VARIANT[detail.status] ?? "muted"} size="sm" dot>{detail.status_label}</Badge>
          <Badge variant={PRIORITY_VARIANT[detail.priority] ?? "muted"} size="sm">{detail.priority}</Badge>
          {detail.is_critical_incident && <Badge variant="danger" size="sm">Critical incident</Badge>}
          <span style={{ flex: 1 }} />
          <Btn size="xs" variant="ghost" icon={<RefreshCw size={12} />} onClick={onRefresh} />
        </div>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{detail.subject}</h3>
      </div>

      <div style={{ padding: "12px 16px", display: "grid", gridTemplateColumns: "130px 1fr", gap: "7px 10px", fontSize: 12.5, borderBottom: "1px solid var(--border)" }}>
        <span style={ROW_LABEL}>Category</span><span>{detail.category_label}{detail.subcategory ? ` — ${detail.subcategory}` : ""}</span>
        <span style={ROW_LABEL}>Impact</span><span>{detail.impact_label}</span>
        <span style={ROW_LABEL}>Reporter</span><span>{detail.reporter_name ?? "—"} {detail.reporter_role ? `(${detail.reporter_role})` : ""}</span>
        <span style={ROW_LABEL}>ServiceOS team</span><span>{detail.assigned_team ?? "Awaiting triage"}{detail.assigned_admin_name ? ` — ${detail.assigned_admin_name}` : ""}</span>
        <span style={ROW_LABEL}>Vertical</span><span>{detail.vertical_key ?? "Platform-wide"}</span>
        <span style={ROW_LABEL}>Created</span><span>{fmt(detail.created_at)}</span>
        <span style={ROW_LABEL}>Updated</span><span>{fmt(detail.updated_at)}</span>
        {detail.affected_feature && (<><span style={ROW_LABEL}>Affected</span><span>{detail.affected_feature}</span></>)}
        {Object.keys(detail.related_entities).length > 0 && (
          <>
            <span style={ROW_LABEL}>Related</span>
            <span style={{ fontFamily: "monospace", fontSize: 11.5 }}>
              {Object.entries(detail.related_entities).map(([k, v]) => `${k}: ${v}`).join(" · ")}
            </span>
          </>
        )}
      </div>

      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <Activity size={14} color="var(--text-tertiary)" />
          <strong style={{ fontSize: 12 }}>Service level</strong>
          <Badge variant={SLA_VARIANT[detail.sla.breach_state] ?? "muted"} size="sm">{detail.sla.display_message}</Badge>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, fontSize: 11.5 }}>
          <div><div style={ROW_LABEL}>First response</div><div>{detail.sla.first_response_met_at ? `Met ${fmt(detail.sla.first_response_met_at)}` : fmt(detail.sla.first_response_due_at)}</div></div>
          <div><div style={ROW_LABEL}>Next update</div><div>{fmt(detail.sla.next_update_due_at)}</div></div>
          <div><div style={ROW_LABEL}>Resolution target</div><div>{detail.sla.resolution_target_at ? fmt(detail.sla.resolution_target_at) : "Not applicable"}</div></div>
        </div>
        <div style={{ marginTop: 6, fontSize: 10.5, color: "var(--text-tertiary)" }}>Policy: {detail.sla.sla_policy}</div>
      </div>

      {detail.resolution_summary && (
        <div style={{ padding: "12px 16px", background: "var(--success-bg)", borderBottom: "1px solid var(--success-border)" }}>
          <div style={{ display: "flex", gap: 7, alignItems: "center", marginBottom: 5 }}>
            <CheckCircle2 size={15} color="var(--success-text)" />
            <strong style={{ fontSize: 12.5, color: "var(--success-text)" }}>Resolution</strong>
          </div>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--success-text)" }}>{detail.resolution_summary}</p>
        </div>
      )}

      <div style={{ padding: "12px 16px", maxHeight: 340, overflowY: "auto" }}>
        <strong style={{ fontSize: 12, display: "block", marginBottom: 10 }}>Conversation</strong>
        {detail.conversation.map(m => {
          const mine = m.author_type === "tenant";
          const sys = m.author_type === "system";
          return (
            <div key={m.id} style={{
              borderLeft: `2px solid ${sys ? "var(--border)" : mine ? "var(--accent)" : "var(--success-border)"}`,
              paddingLeft: 10, marginBottom: 12,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, fontWeight: 700 }}>{m.author_name}</span>
                {m.kind === "information_request" && <Badge variant="warning" size="sm">Information requested</Badge>}
                {m.kind === "resolution_summary" && <Badge variant="success" size="sm">Resolution</Badge>}
                {m.kind === "system_event" && <Badge variant="muted" size="sm">System</Badge>}
                <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>{fmt(m.created_at)}</span>
              </div>
              <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>{m.body}</p>
              {m.attachments.length > 0 && (
                <div style={{ marginTop: 5, fontSize: 11.5, color: "var(--text-secondary)" }}>
                  <Paperclip size={11} style={{ verticalAlign: -1 }} />{" "}
                  {m.attachments.map(x => x.file_name).filter(Boolean).join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {detail.status_history.length > 0 && (
        <details style={{ padding: "0 16px 12px" }}>
          <summary style={{ fontSize: 12, fontWeight: 700, cursor: "pointer", color: "var(--text-secondary)" }}>
            Status history ({detail.status_history.length})
          </summary>
          <div style={{ marginTop: 8 }}>
            {detail.status_history.map(h => (
              <div key={h.id} style={{ fontSize: 11.5, color: "var(--text-secondary)", padding: "3px 0" }}>
                {fmt(h.created_at)} — <strong>{h.event_type.replace(/_/g, " ")}</strong>
                {h.from || h.to ? `: ${h.from ?? "—"} → ${h.to ?? "—"}` : ""}
                {h.actor_name ? ` · ${h.actor_name}` : ""}
                {h.reason ? ` · ${h.reason}` : ""}
              </div>
            ))}
          </div>
        </details>
      )}

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
        {actionErr && (
          <div style={{
            marginBottom: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
            borderRadius: 8, padding: "8px 11px", fontSize: 12, color: "var(--danger-text)",
          }}>{actionErr}</div>
        )}
        {a.can_reply && canReply && (
          <>
            <Input label={a.can_provide_information ? "Provide the requested information" : "Add a reply"}
              value={reply} onChange={setReply} rows={3}
              placeholder="Reply to ServiceOS support…" />
            <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
              <Btn size="sm" onClick={sendReply} loading={busy} disabled={busy || !reply.trim()} icon={<Send size={13} />}>
                Send reply
              </Btn>
              {a.can_escalate && (
                <Btn size="sm" variant="danger" onClick={() => act(() => supportApi.escalate(detail.id))} disabled={busy}>
                  Escalate (SLA breached)
                </Btn>
              )}
            </div>
          </>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: a.can_reply && canReply ? 10 : 0, flexWrap: "wrap" }}>
          {a.can_confirm_resolution && (
            <Btn size="sm" variant="success" onClick={() => act(() => supportApi.confirmResolution(detail.id))} disabled={busy}>
              Confirm resolution
            </Btn>
          )}
          {a.can_reopen && (
            <Btn size="sm" variant="secondary" disabled={busy}
              onClick={() => act(() => supportApi.reopen(detail.id, "Reopened by the tenant — the problem is still occurring."))}>
              Reopen
            </Btn>
          )}
        </div>
        {!a.can_reply && !a.can_confirm_resolution && !a.can_reopen && (
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>
            This request is closed. {a.reopen_deadline_at
              ? `It could be reopened until ${fmtDate(a.reopen_deadline_at)}.`
              : "Create a new request if you still need help."}
          </p>
        )}
      </div>
    </Card>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────
function HelpSupportPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = (params.get("tab") as Tab) || "requests";
  const ticketParam = params.get("ticket");
  const areaParam = params.get("area");

  const [ws, setWs] = useState<SupportWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<string | null>(ticketParam);
  const [detail, setDetail] = useState<SupportRequestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [helpQuery, setHelpQuery] = useState("");
  const [kb, setKb] = useState<SupportKnowledge | null>(null);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbError, setKbError] = useState<string | null>(null);

  const [fCategory, setFCategory] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fPriority, setFPriority] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [criticalOpen, setCriticalOpen] = useState(false);

  const setTab = (t: Tab) => {
    const q = new URLSearchParams(Array.from(params.entries()));
    q.set("tab", t);
    router.replace(`/help-support?${q.toString()}`, { scroll: false });
  };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setWs(await supportApi.workspace()); }
    catch (e) {
      setError(e instanceof ServiceOSError
        ? e.message
        : "Support is temporarily unavailable. Please retry in a moment.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const loadDetail = useCallback(async (id: string) => {
    setDetailLoading(true); setDetailError(null);
    try { setDetail(await supportApi.getRequest(id)); }
    catch (e) {
      setDetail(null);
      setDetailError(e instanceof ServiceOSError ? e.message : "This request could not be loaded.");
    } finally { setDetailLoading(false); }
  }, []);

  useEffect(() => { if (selected) void loadDetail(selected); else setDetail(null); }, [selected, loadDetail]);

  const loadKb = useCallback(async (q: string, area: string | null) => {
    setKbLoading(true); setKbError(null);
    try { setKb(await supportApi.knowledge({ search: q || undefined, area: area || undefined })); }
    catch (e) { setKbError(e instanceof ServiceOSError ? e.message : "Help articles could not be loaded."); }
    finally { setKbLoading(false); }
  }, []);

  useEffect(() => {
    if (tab === "knowledge") void loadKb(helpQuery, areaParam);
  }, [tab, areaParam, loadKb, helpQuery]);

  const runHelpSearch = () => {
    const q = new URLSearchParams(Array.from(params.entries()));
    q.set("tab", "knowledge");
    router.replace(`/help-support?${q.toString()}`, { scroll: false });
    void loadKb(helpQuery, areaParam);
  };

  const rows = useMemo(() => {
    if (!ws) return [];
    const s = search.trim().toLowerCase();
    return ws.requests.filter(r =>
      (!s || r.subject.toLowerCase().includes(s) || r.ticket_number.toLowerCase().includes(s)) &&
      (!fCategory || r.category === fCategory) &&
      (!fStatus || (fStatus === "open"
        ? !["resolved", "closed", "withdrawn"].includes(r.status)
        : r.status === fStatus)) &&
      (!fPriority || r.priority === fPriority));
  }, [ws, search, fCategory, fStatus, fPriority]);

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Skeleton height={30} width={260} /><div style={{ height: 8 }} />
        <Skeleton height={16} width={420} /><div style={{ height: 18 }} />
        <Skeleton height={46} /><div style={{ height: 14 }} />
        <Skeleton height={44} /><div style={{ height: 14 }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} height={86} />)}
        </div>
        <div style={{ height: 16 }} /><Skeleton height={220} />
      </div>
    );
  }

  if (error || !ws) {
    return (
      <div style={{ padding: 24 }}>
        <Card padding={22}>
          <EmptyState icon={<AlertCircle size={26} />} title="Help & Support is unavailable"
            description={error ?? "Please try again."}
            action={<Btn icon={<RefreshCw size={14} />} onClick={() => void load()}>Retry</Btn>} />
        </Card>
      </div>
    );
  }

  if (!ws.permissions.can_view) {
    return (
      <div style={{ padding: 24 }}>
        <Card padding={22}>
          <EmptyState icon={<Shield size={26} />} title="You do not have access to support requests"
            description="Ask an owner in your workspace to grant you support access." />
        </Card>
      </div>
    );
  }

  const p = ws.permissions;

  return (
    <div style={{ padding: 24, maxWidth: 1560, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ flex: 1, minWidth: 280 }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>Help &amp; Support</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
            Find answers, report a platform issue and track your support requests.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={14} />} onClick={() => void load()}>Refresh</Btn>
          {p.can_create && (
            <Btn icon={<Plus size={15} />} onClick={() => setCreateOpen(true)}>Create support request</Btn>
          )}
        </div>
      </div>

      <StatusBanner status={ws.service_status} />

      {/* Help search */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 280 }}>
          <Search size={15} style={{ position: "absolute", left: 12, top: 12, color: "var(--text-tertiary)" }} />
          <input
            value={helpQuery}
            onChange={e => setHelpQuery(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") runHelpSearch(); }}
            placeholder="Search help articles, setup guides and troubleshooting…"
            style={{
              width: "100%", padding: "10px 12px 10px 34px", fontSize: 13,
              border: "1px solid var(--border)", borderRadius: 10,
              background: "var(--surface)", color: "var(--text-primary)", outline: "none",
            }} />
        </div>
        <Btn variant="secondary" onClick={runHelpSearch} icon={<BookOpen size={14} />}>Search help</Btn>
      </div>

      {/* Quick help */}
      <h2 style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Quick help</h2>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
        gap: 10, marginBottom: 20,
      }}>
        {ws.quick_help.map(c => (
          <Link key={c.key} href={c.href} style={{ textDecoration: "none" }}>
            <Card padding={13} hover style={{ height: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                <span style={{ color: "var(--brand)" }}>{QUICK_HELP_ICONS[c.icon] ?? <BookOpen size={16} />}</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{c.label}</strong>
              </div>
              <p style={{ margin: "0 0 8px", fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.45 }}>{c.description}</p>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                  {c.has_content ? `${c.article_count} guide${c.article_count === 1 ? "" : "s"}` : "No guides published yet"}
                </span>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--brand)", display: "inline-flex", alignItems: "center", gap: 2 }}>
                  View guides <ChevronRight size={12} />
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map(t => {
          const active = tab === t.id;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "9px 14px", fontSize: 13, fontWeight: active ? 700 : 600,
              color: active ? "var(--brand)" : "var(--text-secondary)",
              background: "none", border: "none", cursor: "pointer",
              borderBottom: `2px solid ${active ? "var(--brand)" : "transparent"}`, marginBottom: -1,
            }}>
              {t.label}
              {t.id === "requests" && ws.summary.open > 0 && (
                <span style={{ marginLeft: 6 }}><Badge variant="info" size="sm">{ws.summary.open}</Badge></span>
              )}
              {t.id === "announcements" && ws.announcements.some(a => a.requires_acknowledgement && !a.acknowledged) && (
                <span style={{ marginLeft: 6 }}><Badge variant="warning" size="sm">Action</Badge></span>
              )}
            </button>
          );
        })}
      </div>

      {tab === "requests" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12, marginBottom: 14 }}>
            {[
              { label: "Open", value: ws.summary.open, variant: "info" as const, icon: <Clock size={15} /> },
              { label: "Awaiting your reply", value: ws.summary.awaiting_your_reply, variant: "warning" as const, icon: <AlertTriangle size={15} /> },
              { label: "Resolved", value: ws.summary.resolved, variant: "success" as const, icon: <CheckCircle2 size={15} /> },
            ].map(s => (
              <Card key={s.label} padding={14}>
                <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6, color: "var(--text-tertiary)" }}>
                  {s.icon}<span style={ROW_LABEL}>{s.label}</span>
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>{s.value}</div>
              </Card>
            ))}
          </div>

          <div style={{
            background: "var(--info-bg)", border: "1px solid var(--info-border)", borderRadius: 9,
            padding: "9px 13px", fontSize: 12.5, color: "var(--info-text)", marginBottom: 14,
            display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
          }}>
            <AlertCircle size={14} />
            <span>{ws.complaints_redirect.message}</span>
            <Link href={ws.complaints_redirect.href} style={{ fontWeight: 700, color: "inherit" }}>Open Complaints →</Link>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.35fr) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
            <div>
              <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
                <div style={{ position: "relative", flex: 1, minWidth: 180 }}>
                  <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--text-tertiary)" }} />
                  <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search your requests…"
                    style={{
                      width: "100%", padding: "8px 10px 8px 30px", fontSize: 12.5,
                      border: "1px solid var(--border)", borderRadius: 8,
                      background: "var(--surface)", color: "var(--text-primary)", outline: "none",
                    }} />
                </div>
                <select aria-label="Filter support requests by category" value={fCategory} onChange={e => setFCategory(e.target.value)} style={selectStyle}>
                  <option value="">All categories</option>
                  {ws.form_options.categories.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
                </select>
                <select aria-label="Filter support requests by status" value={fStatus} onChange={e => setFStatus(e.target.value)} style={selectStyle}>
                  <option value="">All statuses</option>
                  <option value="open">Open only</option>
                  {ws.statuses.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <select aria-label="Filter support requests by priority" value={fPriority} onChange={e => setFPriority(e.target.value)} style={selectStyle}>
                  <option value="">All priorities</option>
                  {ws.priorities.map(x => <option key={x} value={x}>{x}</option>)}
                </select>
              </div>

              <Card padding={0} style={{ overflow: "hidden" }}>
                {rows.length === 0 ? (
                  <div style={{ padding: 22 }}>
                    <EmptyState icon={<LifeBuoy size={24} />}
                      title={ws.requests.length === 0 ? "No support requests yet" : "No requests match these filters"}
                      description={ws.requests.length === 0
                        ? "When you need help with your ServiceOS account or the platform, create a support request and track it here."
                        : "Clear a filter to see more of your requests."}
                      action={ws.requests.length === 0 && p.can_create
                        ? <Btn icon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Create support request</Btn>
                        : undefined} />
                  </div>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <TableSurface style={{ width: "100%", borderCollapse: "collapse", minWidth: 860 }}>
                      <thead>
                        <tr>
                          <th style={TH}>Ticket</th>
                          <th style={TH}>Subject</th>
                          <th style={TH}>Category</th>
                          <th style={TH}>Priority</th>
                          <th style={TH}>Status</th>
                          <th style={TH}>Submitted by</th>
                          <th style={TH}>Assigned team</th>
                          <th style={TH}>SLA / next update</th>
                          <th style={TH}>Updated</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map(r => {
                          const active = selected === r.id;
                          return (
                            <tr key={r.id} onClick={() => setSelected(r.id)} style={{
                              cursor: "pointer",
                              background: active ? "var(--accent-muted)" : "transparent",
                            }}>
                              <td style={{ ...TD, fontFamily: "monospace", fontSize: 11.5, whiteSpace: "nowrap" }}>
                                {r.ticket_number}
                                {r.unread_updates > 0 && <span style={{ marginLeft: 5 }}><Badge variant="danger" size="sm">{r.unread_updates}</Badge></span>}
                              </td>
                              <td style={{ ...TD, maxWidth: 260 }}>
                                <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>
                                  {r.is_critical_incident && <AlertTriangle size={12} color="var(--danger-text)" style={{ verticalAlign: -1, marginRight: 4 }} />}
                                  {r.subject}
                                </span>
                              </td>
                              <td style={{ ...TD, whiteSpace: "nowrap" }}>{r.category_label}</td>
                              <td style={TD}><Badge variant={PRIORITY_VARIANT[r.priority] ?? "muted"} size="sm">{r.priority}</Badge></td>
                              <td style={TD}><Badge variant={STATUS_VARIANT[r.status] ?? "muted"} size="sm" dot>{r.status_label}</Badge></td>
                              <td style={{ ...TD, whiteSpace: "nowrap" }}>{r.reporter_name ?? "—"}</td>
                              <td style={{ ...TD, whiteSpace: "nowrap", fontSize: 11.5 }}>{r.assigned_team ?? "Awaiting triage"}</td>
                              <td style={TD}>
                                <Badge variant={SLA_VARIANT[r.sla_breach_state] ?? "muted"} size="sm">{r.sla_display}</Badge>
                              </td>
                              <td style={{ ...TD, whiteSpace: "nowrap", fontSize: 11.5, color: "var(--text-secondary)" }}>{fmt(r.updated_at)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </TableSurface>
                  </div>
                )}
              </Card>
            </div>

            <div style={{ display: "grid", gap: 14 }}>
              <RequestDetailPanel detail={detail} loading={detailLoading} error={detailError}
                canReply={p.can_reply}
                onRefresh={() => { if (selected) void loadDetail(selected); void load(); }} />

              {ws.recommended_articles.length > 0 && (
                <Card padding={14}>
                  <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
                    <BookOpen size={15} color="var(--brand)" />
                    <strong style={{ fontSize: 13 }}>Recommended articles</strong>
                  </div>
                  {ws.recommended_articles.map(a => (
                    <div key={a.id} style={{ padding: "7px 0", borderTop: "1px solid var(--border)" }}>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{a.title}</div>
                      <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>{a.summary}</div>
                    </div>
                  ))}
                  <div style={{ marginTop: 10 }}>
                    <Btn size="xs" variant="ghost" onClick={() => setTab("knowledge")}>
                      Browse all {ws.knowledge_total} guides →
                    </Btn>
                  </div>
                </Card>
              )}

              {p.can_report_critical_incident && (
                <Card padding={14} style={{ borderColor: "var(--danger-border)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6 }}>
                    <ShieldAlert size={15} color="var(--danger-text)" />
                    <strong style={{ fontSize: 13, color: "var(--danger-text)" }}>Critical incident</strong>
                  </div>
                  <p style={{ margin: "0 0 10px", fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.45 }}>
                    Only for an outage, confirmed data loss or a serious security incident. Rate-limited
                    and routed straight to ServiceOS incident response.
                  </p>
                  <Btn size="sm" variant="danger" onClick={() => setCriticalOpen(true)}>Report critical incident</Btn>
                </Card>
              )}
            </div>
          </div>
        </>
      )}

      {tab === "knowledge" && (
        <div>
          {kbLoading && <Skeleton height={200} />}
          {kbError && (
            <Card padding={20}>
              <EmptyState icon={<AlertCircle size={24} />} title="Help articles unavailable" description={kbError}
                action={<Btn size="sm" onClick={() => void loadKb(helpQuery, areaParam)} icon={<RefreshCw size={13} />}>Retry</Btn>} />
            </Card>
          )}
          {!kbLoading && !kbError && kb && (
            kb.articles.length === 0 ? (
              <Card padding={22}>
                <EmptyState icon={<BookOpen size={24} />} title="No matching guides"
                  description={`Nothing matched "${kb.search ?? ""}". Try a different word, or create a support request and we will help directly.`}
                  action={p.can_create ? <Btn size="sm" onClick={() => setCreateOpen(true)} icon={<Plus size={13} />}>Create support request</Btn> : undefined} />
              </Card>
            ) : (
              <>
                {areaParam && (
                  <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                    <Badge variant="default" size="md">
                      {kb.categories.find(c => c.key === areaParam)?.label ?? areaParam}
                    </Badge>
                    <Btn size="xs" variant="ghost" icon={<X size={12} />}
                      onClick={() => router.replace("/help-support?tab=knowledge", { scroll: false })}>Clear</Btn>
                  </div>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(330px, 1fr))", gap: 12 }}>
                  {kb.articles.map(a => <ArticleCard key={a.id} article={a} />)}
                </div>
              </>
            )
          )}
        </div>
      )}

      {tab === "announcements" && (
        <AnnouncementsTab items={ws.announcements} onChanged={() => void load()} />
      )}

      <CreateRequestDrawer open={createOpen} onClose={() => setCreateOpen(false)} ws={ws}
        onCreated={d => { setSelected(d.id); setDetail(d); setTab("requests"); void load(); }} />
      <CriticalIncidentModal open={criticalOpen} onClose={() => setCriticalOpen(false)} ws={ws}
        onCreated={d => { setSelected(d.id); setDetail(d); setTab("requests"); void load(); }} />
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: "8px 10px", fontSize: 12.5, border: "1px solid var(--border)",
  borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)", outline: "none",
};

function ArticleCard({ article }: { article: SupportArticle }) {
  const [open, setOpen] = useState(false);
  const [voted, setVoted] = useState<boolean | null>(null);
  return (
    <Card padding={14}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
        <BookOpen size={15} color="var(--brand)" style={{ marginTop: 2, flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 13.5, color: "var(--text-primary)" }}>{article.title}</strong>
          {article.is_featured && <span style={{ marginLeft: 6 }}><Badge variant="golden" size="sm">Featured</Badge></span>}
        </div>
      </div>
      <p style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{article.summary}</p>
      {open && article.body && (
        <p style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--text-primary)", lineHeight: 1.55 }}>{article.body}</p>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <Btn size="xs" variant="ghost" onClick={() => setOpen(o => !o)}>{open ? "Hide" : "Read guide"}</Btn>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>Updated {fmtDate(article.updated_at)}</span>
        {voted === null ? (
          <>
            <Btn size="xs" variant="ghost" onClick={async () => { setVoted(true); try { await supportApi.articleFeedback(article.id, true); } catch { /* feedback is best-effort */ } }}>Helpful</Btn>
            <Btn size="xs" variant="ghost" onClick={async () => { setVoted(false); try { await supportApi.articleFeedback(article.id, false); } catch { /* feedback is best-effort */ } }}>Not helpful</Btn>
          </>
        ) : (
          <span style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>Thanks for the feedback</span>
        )}
      </div>
    </Card>
  );
}

const ANN_VARIANT: Record<string, "info" | "success" | "warning" | "danger" | "muted"> = {
  planned_maintenance: "info", feature_release: "success", policy_update: "warning",
  known_issue: "danger", resolved_incident: "success", vertical_notice: "info",
};

function AnnouncementsTab({ items, onChanged }: { items: SupportAnnouncementItem[]; onChanged: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  if (items.length === 0) {
    return (
      <Card padding={22}>
        <EmptyState icon={<Megaphone size={24} />} title="No announcements"
          description="Planned maintenance, feature releases and policy updates that apply to your workspace will appear here." />
      </Card>
    );
  }
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {items.map(a => (
        <Card key={a.id} padding={15} style={a.requires_acknowledgement && !a.acknowledged ? { borderColor: "var(--warning-border)" } : undefined}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
            <Megaphone size={15} color="var(--brand)" />
            <Badge variant={ANN_VARIANT[a.announcement_type] ?? "muted"} size="sm">
              {a.announcement_type.replace(/_/g, " ")}
            </Badge>
            {a.is_expired && <Badge variant="muted" size="sm">Past</Badge>}
            {a.requires_acknowledgement && (
              <Badge variant={a.acknowledged ? "success" : "warning"} size="sm">
                {a.acknowledged ? "Acknowledged" : "Acknowledgement required"}
              </Badge>
            )}
            <span style={{ flex: 1 }} />
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{fmtDate(a.effective_from)}</span>
          </div>
          <strong style={{ fontSize: 13.5, color: "var(--text-primary)", display: "block", marginBottom: 4 }}>{a.title}</strong>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{a.body}</p>
          {a.requires_acknowledgement && !a.acknowledged && (
            <div style={{ marginTop: 10 }}>
              <Btn size="sm" variant="warning" loading={busy === a.id}
                onClick={async () => {
                  setBusy(a.id);
                  try { await supportApi.acknowledgeAnnouncement(a.id); onChanged(); }
                  finally { setBusy(null); }
                }}>Acknowledge</Btn>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

/**
 * Real build failure fixed here: this page calls `useSearchParams()`, which
 * Next.js requires to sit inside a Suspense boundary -- without one, static
 * prerendering of /help-support threw "useSearchParams() should be wrapped in
 * a suspense boundary" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * The boundary is scoped to this page rather than added to the layout so the
 * rest of the tenant shell keeps prerendering normally.
 */
export default function HelpSupportPage() {
  return (
    <Suspense fallback={null}>
      <HelpSupportPageInner />
    </Suspense>
  );
}
