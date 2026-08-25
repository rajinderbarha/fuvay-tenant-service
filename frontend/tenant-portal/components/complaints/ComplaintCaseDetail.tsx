"use client";
/** Complaint case detail.
 *
 * Conversation/Evidence/Resolution were placeholders reading "ships in a later
 * phase". Two of the three endpoints they needed already existed on the
 * secured provider router (`/messages`, `/respond`, `/resolutions`,
 * `/offer-resolution`); the third (evidence) had a service method
 * (`ComplaintService.list_media`) that no router exposed, so customer-attached
 * photos were stored and unreachable. All three are now real. */
import React, { useCallback } from "react";
import { Wrench, CreditCard, Lock } from "lucide-react";
import { Card, Badge, Skeleton } from "../shared/ui";
import { tenantComplaintsApi, type ComplaintDetail } from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { ConversationTab, EvidenceTab, ResolutionTab } from "./ComplaintCaseTabs";
import { severityVariant, slaVariant, statusLabel } from "./ComplaintQueueList";

const TABS = ["overview", "conversation", "evidence", "job-context", "resolution", "activity"] as const;
export type ComplaintTab = typeof TABS[number];
const TAB_LABELS: Record<ComplaintTab, string> = {
  overview: "Overview", conversation: "Conversation", evidence: "Evidence",
  "job-context": "Job Context", resolution: "Resolution", activity: "Activity & Audit",
};

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function ComplaintCaseDetail({ complaintId, tab, onTabChange }: {
  complaintId: string; tab: ComplaintTab; onTabChange: (t: ComplaintTab) => void;
}) {
  const detail = useApi(useCallback(() => tenantComplaintsApi.detail(complaintId), [complaintId]));
  const jobContext = useApi(useCallback(() => tenantComplaintsApi.jobContext(complaintId), [complaintId]));
  const activity = useApi(useCallback(() => tenantComplaintsApi.activity(complaintId), [complaintId]));

  const c: ComplaintDetail | null = detail.data;

  return (
    <Card padding={0} style={{ flex: 1, minWidth: 0 }}>
      <div style={{ padding: 20 }}>
        {detail.loading ? <Skeleton height={300}/> : !c ? (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {detail.error ?? "This complaint could not be loaded."}
          </p>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <div>
                <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                  {c.complaint_number} — {c.title ?? c.complaint_type.replace(/_/g, " ")}
                </h2>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{c.customer_alias}</p>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <Badge variant={severityVariant(c.severity)} size="sm">{c.severity}</Badge>
                <Badge variant={slaVariant(c.sla_status)} size="sm">{statusLabel(c.sla_status)}</Badge>
                <Badge variant="info" size="sm">{statusLabel(c.status)}</Badge>
              </div>
            </div>

            <div style={{ display: "flex", gap: 6, borderBottom: "1px solid var(--border)", margin: "16px 0", overflowX: "auto" }}>
              {TABS.map(t => (
                <button key={t} onClick={() => onTabChange(t)} style={{
                  padding: "8px 10px", background: "none", border: "none", cursor: "pointer", whiteSpace: "nowrap",
                  fontSize: 12, fontWeight: tab === t ? 700 : 500,
                  color: tab === t ? "var(--brand)" : "var(--text-tertiary)",
                  borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
                }}>
                  {TAB_LABELS[t]}
                </button>
              ))}
            </div>

            {tab === "overview" && <OverviewTab c={c}/>}
            {tab === "job-context" && (
              jobContext.loading ? <Skeleton height={200}/> : <JobContextTab data={jobContext.data}/>
            )}
            {tab === "activity" && (
              activity.loading ? <Skeleton height={200}/> : (
                <div>
                  {(activity.data?.items ?? []).length === 0 ? (
                    <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No activity recorded yet.</p>
                  ) : activity.data!.items.map(e => (
                    <div key={e.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                      <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: "0 0 2px" }}>
                        {e.event_type.replace(/_/g, " ")}
                        {e.old_status && e.new_status ? ` (${e.old_status} → ${e.new_status})` : ""}
                      </p>
                      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                        {fmtDate(e.created_at)} · {e.actor_type}
                      </p>
                    </div>
                  ))}
                </div>
              )
            )}
            {tab === "conversation" && (
              <ConversationTab complaintId={complaintId} canReply={c.available_actions.includes("SEND_MESSAGE")}/>
            )}
            {tab === "evidence" && <EvidenceTab complaintId={complaintId}/>}
            {tab === "resolution" && (
              <ResolutionTab
                complaintId={complaintId}
                canOffer={c.available_actions.includes("OFFER_RESOLUTION")}
                blockedReason={c.action_blocked_reason ?? null}
                onChanged={() => detail.refetch()}
              />
            )}
          </>
        )}
      </div>
    </Card>
  );
}

function OverviewTab({ c }: { c: ComplaintDetail }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 8px" }}>Customer statement</p>
        <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5 }}>{c.description}</p>
      </div>
      {c.job && (
        <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <Wrench size={13} style={{ color: "var(--text-tertiary)" }}/>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{c.job.job_number}</span>
            <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>{c.job.master_service_name ?? "Service"}</span>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            Technician: {c.job.technician_name ?? "Unassigned"} · Job status: {statusLabel(c.job.status)}
          </p>
        </div>
      )}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Created</p>
          <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0 }}>{fmtDate(c.created_at)}</p>
        </div>
        <div>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Last activity</p>
          <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0 }}>{fmtDate(c.updated_at)}</p>
        </div>
        {c.tenant_first_response_due_at && (
          <div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>Response due</p>
            <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0 }}>{fmtDate(c.tenant_first_response_due_at)}</p>
          </div>
        )}
      </div>
      {/* This used to list raw next-STATUSES from the state machine and call
          them "available next states". None of them were things a tenant could
          do -- there is no tenant status-transition endpoint -- so it described
          capabilities that did not exist. It now lists the real actions. */}
      {c.available_actions.length > 0 && (
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 8px" }}>What you can do</p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {c.available_actions.includes("SEND_MESSAGE") && <Badge variant="info" size="sm">Reply to customer</Badge>}
            {c.available_actions.includes("OFFER_RESOLUTION") && <Badge variant="success" size="sm">Propose resolution</Badge>}
          </div>
          {c.action_blocked_reason && (
            <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginTop: 8, display: "flex", gap: 6, alignItems: "flex-start" }}>
              <Lock size={11} style={{ marginTop: 2, flexShrink: 0 }}/>{c.action_blocked_reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function JobContextTab({ data }: { data: import("../../lib/api").ComplaintJobContext | null }) {
  if (!data || !data.available) {
    return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{data?.reason ?? "No job context available."}</p>;
  }
  const j = data.job!;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Job number" value={j.job_number}/>
        <Field label="Service" value={j.master_service_name ?? "—"}/>
        <Field label="Technician" value={j.technician_name ?? "Unassigned"}/>
        <Field label="Job status" value={statusLabel(j.status)}/>
        <Field label="Assignment" value={statusLabel(j.assignment_status)}/>
        <Field label="Scheduled" value={j.scheduled_date ?? "—"}/>
        <Field label="Locality" value={[j.city, j.zipcode].filter(Boolean).join(", ") || "—"}/>
      </div>
      <div>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 6 }}>
          <CreditCard size={12}/> Direct payment
        </p>
        {(data.direct_payments ?? []).length === 0 ? (
          <p style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>No direct-payment record linked to this job.</p>
        ) : data.direct_payments!.map(p => (
          <div key={p.payment_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>₹{Number(p.collected_amount).toLocaleString("en-IN")} · {p.payment_mode}</span>
            <Badge variant={p.customer_confirmed ? "success" : "warning"} size="sm">{p.customer_confirmed ? "Confirmed" : "Pending"}</Badge>
          </div>
        ))}
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>
          Paid directly to the provider. ServiceOS records confirmation only.
        </p>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: 12.5, color: "var(--text-primary)", margin: 0 }}>{value}</p>
    </div>
  );
}
