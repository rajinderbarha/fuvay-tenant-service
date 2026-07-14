"use client";
/**
 * MODULE-L5-02 — Provider Complaint Detail.
 *
 * The complaints list page has always had a "View & Respond" row action linking
 * to /provider/complaints/{id}, but that page did not exist — it was a dead 404.
 * So the provider-facing complaint workflow (respond, offer a resolution, and
 * the settlement-proposal exchange) had no UI at all, even though every endpoint
 * behind it exists.
 *
 * Backs: GET  /v1/provider/complaints/{id}
 *        GET  /v1/provider/complaints/{id}/messages
 *        POST /v1/provider/complaints/{id}/respond
 *        GET  /v1/provider/complaints/{id}/resolutions
 *        POST /v1/provider/complaints/{id}/offer-resolution
 *        GET  /v1/provider/complaints/{id}/settlement-proposals
 *        POST /v1/provider/complaints/{id}/settlement-proposals
 *        POST /v1/provider/complaints/{id}/settlement-proposals/{pid}/respond
 */
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import {
  Card, CardHeader, SectionHeader, Btn, Badge, Spinner, Input, Select, Modal,
} from "../../../../../components/shared/ui";
import { apiFetch } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

type BV = "default" | "success" | "warning" | "danger" | "info" | "muted";

const STATUS_COLOR: Record<string, BV> = {
  open:                       "warning",
  awaiting_provider_response: "danger",
  awaiting_customer_response: "info",
  under_admin_review:         "warning",
  resolution_proposed:        "info",
  rework_approved:            "info",
  refund_requested:           "warning",
  refund_approved:            "info",
  refund_recorded:            "info",
  resolved:                   "success",
  settled:                    "success",
  closed:                     "muted",
  rejected:                   "danger",
  cancelled:                  "muted",
};

const SLA_COLOR: Record<string, BV> = {
  on_time:   "success",
  at_risk:   "warning",
  breached:  "danger",
  escalated: "danger",
};

const RESOLUTION_TYPES = [
  { value: "rework",                label: "Free rework visit" },
  { value: "refund",                label: "Refund" },
  { value: "callback",              label: "Callback" },
  { value: "provider_reassignment", label: "Reassign provider" },
  { value: "apology",               label: "Apology" },
  { value: "no_action",             label: "No action" },
];

const PROPOSAL_TYPES = [
  { value: "partial_refund", label: "Partial refund" },
  { value: "full_refund",    label: "Full refund" },
  { value: "free_rework",    label: "Free rework" },
  { value: "credit",         label: "Account credit" },
  { value: "no_action",      label: "No action" },
];

type Dict = Record<string, unknown>;
const s = (v: unknown) => (v == null ? "" : String(v));

export default function ProviderComplaintDetailPage() {
  const params = useParams();
  const id = String(params?.complaint_id ?? "");

  const [tab, setTab] = useState<"messages" | "resolutions" | "settlement">("messages");
  const [reply, setReply] = useState("");
  const [resOpen, setResOpen] = useState(false);
  const [resType, setResType] = useState("rework");
  const [resDesc, setResDesc] = useState("");
  const [propOpen, setPropOpen] = useState(false);
  const [propType, setPropType] = useState("partial_refund");
  const [propDesc, setPropDesc] = useState("");
  const [propAmt, setPropAmt] = useState("");

  const complaint = useApi<Dict>(
    useCallback(() => apiFetch<Dict>(`/v1/provider/complaints/${id}`), [id]), [id]);
  const messages = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/messages`), [id]), [id]);
  const resolutions = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/resolutions`), [id]), [id]);
  const proposals = useApi<Dict[]>(
    useCallback(() => apiFetch<Dict[]>(`/v1/provider/complaints/${id}/settlement-proposals`), [id]), [id]);

  const refreshAll = () => {
    complaint.refetch(); messages.refetch(); resolutions.refetch(); proposals.refetch();
  };

  const respond = useAction(
    async (text: string) =>
      apiFetch(`/v1/provider/complaints/${id}/respond`, {
        method: "POST", body: JSON.stringify({ message_text: text }),
      }),
    { onSuccess: () => { setReply(""); refreshAll(); } },
  );

  const offerResolution = useAction(
    async () =>
      apiFetch(`/v1/provider/complaints/${id}/offer-resolution`, {
        method: "POST",
        body: JSON.stringify({ resolution_type: resType, description: resDesc }),
      }),
    { onSuccess: () => { setResOpen(false); setResDesc(""); refreshAll(); } },
  );

  const createProposal = useAction(
    async () =>
      apiFetch(`/v1/provider/complaints/${id}/settlement-proposals`, {
        method: "POST",
        body: JSON.stringify({
          proposal_type: propType,
          description: propDesc,
          ...(propAmt ? { proposal_amount: Number(propAmt) } : {}),
        }),
      }),
    { onSuccess: () => { setPropOpen(false); setPropDesc(""); setPropAmt(""); refreshAll(); } },
  );

  const respondProposal = useAction(
    async (pid: string, response: string) =>
      apiFetch(`/v1/provider/complaints/${id}/settlement-proposals/${pid}/respond`, {
        method: "POST", body: JSON.stringify({ response }),
      }),
    { onSuccess: refreshAll },
  );

  const c = complaint.data ?? {};
  const status = s(c.status);
  const sla = s(c.sla_status);

  if (complaint.loading) {
    return <TenantLayout activeNav="provider"><Spinner /></TenantLayout>;
  }
  if (complaint.error) {
    return (
      <TenantLayout activeNav="provider">
        <Card><p style={{ color: "var(--danger)" }}>{complaint.error}</p>
          <Link href="/provider/complaints">← Back to complaints</Link>
        </Card>
      </TenantLayout>
    );
  }

  return (
    <TenantLayout activeNav="provider">
      <div style={{ marginBottom: 12 }}>
        <Link href="/provider/complaints" style={{ fontSize: 13 }}>← Back to complaints</Link>
      </div>

      <SectionHeader
        title={`${s(c.complaint_number) || "Complaint"} — ${s(c.title) || s(c.complaint_type)}`}
        subtitle={s(c.description)}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="secondary" onClick={() => setPropOpen(true)}>Propose settlement</Btn>
            <Btn onClick={() => setResOpen(true)}>Offer resolution</Btn>
          </div>
        }
      />

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <Badge variant={STATUS_COLOR[status] ?? "default"}>{status.replace(/_/g, " ") || "—"}</Badge>
          {sla && <Badge variant={SLA_COLOR[sla] ?? "muted"}>SLA: {sla.replace(/_/g, " ")}</Badge>}
          <Badge variant="muted">{s(c.priority) || "normal"} priority</Badge>
          <Badge variant="muted">{s(c.complaint_type).replace(/_/g, " ")}</Badge>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            Opened {s(c.created_at).slice(0, 10)}
            {c.resolved_at ? ` · Resolved ${s(c.resolved_at).slice(0, 10)}` : ""}
          </span>
        </div>
      </Card>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {(["messages", "resolutions", "settlement"] as const).map(t => (
          <Btn key={t} variant={tab === t ? "primary" : "ghost"} size="sm" onClick={() => setTab(t)}>
            {t === "messages" ? "Messages" : t === "resolutions" ? "Resolutions" : "Settlement"}
          </Btn>
        ))}
      </div>

      {tab === "messages" && (
        <Card>
          <CardHeader title="Conversation" subtitle="Replying marks your first response for SLA purposes." />
          {messages.loading ? <Spinner /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
              {(messages.data ?? []).length === 0 && (
                <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No messages yet.</p>
              )}
              {(messages.data ?? []).map(m => (
                <div key={s(m.id)} style={{
                  padding: "10px 12px", borderRadius: 8,
                  background: s(m.sender_type) === "provider" ? "var(--surface-2)" : "var(--surface)",
                  border: "1px solid var(--border)",
                }}>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
                    {s(m.sender_type)} · {s(m.created_at).slice(0, 16).replace("T", " ")}
                  </div>
                  <div style={{ fontSize: 13 }}>{s(m.message_text)}</div>
                </div>
              ))}
            </div>
          )}
          <Input label="Reply to customer" rows={3} value={reply} onChange={setReply}
                 placeholder="Explain what you will do to resolve this…" />
          {respond.error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{respond.error}</p>}
          <div style={{ marginTop: 10 }}>
            <Btn disabled={!reply.trim() || respond.loading}
                 onClick={() => respond.execute(reply.trim())}>
              {respond.loading ? "Sending…" : "Send reply"}
            </Btn>
          </div>
        </Card>
      )}

      {tab === "resolutions" && (
        <Card>
          <CardHeader title="Resolutions offered"
                      subtitle="A rework resolution, once the customer accepts it, creates a rework request." />
          {resolutions.loading ? <Spinner /> : (
            (resolutions.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No resolution offered yet.</p>
              : (resolutions.data ?? []).map(r => (
                <div key={s(r.id)} style={{
                  padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: 8, marginBottom: 8,
                }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <Badge variant="info">{s(r.resolution_type).replace(/_/g, " ")}</Badge>
                    <Badge variant={s(r.status) === "customer_accepted" ? "success"
                                  : s(r.status) === "customer_rejected" ? "danger" : "muted"}>
                      {s(r.status).replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 13 }}>{s(r.description)}</div>
                </div>
              ))
          )}
        </Card>
      )}

      {tab === "settlement" && (
        <Card>
          <CardHeader title="Settlement proposals"
                      subtitle="A settlement only takes effect once BOTH you and the customer accept it." />
          {proposals.loading ? <Spinner /> : (
            (proposals.data ?? []).length === 0
              ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No settlement proposals yet.</p>
              : (proposals.data ?? []).map(p => {
                const pstatus = s(p.status);
                const mine = s(p.proposed_by) === "provider";
                const awaitingMe = pstatus === "proposed" && !p.tenant_response;
                return (
                  <div key={s(p.id)} style={{
                    padding: "10px 12px", border: "1px solid var(--border)",
                    borderRadius: 8, marginBottom: 8,
                  }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                      <Badge variant="info">{s(p.proposal_type).replace(/_/g, " ")}</Badge>
                      <Badge variant={pstatus === "accepted" ? "success"
                                    : pstatus === "rejected" ? "danger" : "muted"}>
                        {pstatus.replace(/_/g, " ")}
                      </Badge>
                      <Badge variant="muted">by {s(p.proposed_by) || "—"}</Badge>
                      {p.proposal_amount != null && (
                        <Badge variant="muted">₹{s(p.proposal_amount)}</Badge>
                      )}
                    </div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}>{s(p.description)}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      customer: {s(p.customer_response) || "—"} · you: {s(p.tenant_response) || "—"}
                    </div>
                    {awaitingMe && !mine && (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <Btn size="sm" disabled={respondProposal.loading}
                             onClick={() => respondProposal.execute(s(p.id), "accept")}>Accept</Btn>
                        <Btn size="sm" variant="secondary" disabled={respondProposal.loading}
                             onClick={() => respondProposal.execute(s(p.id), "reject")}>Reject</Btn>
                      </div>
                    )}
                  </div>
                );
              })
          )}
          {respondProposal.error && (
            <p style={{ color: "var(--danger)", fontSize: 12 }}>{respondProposal.error}</p>
          )}
        </Card>
      )}

      <Modal open={resOpen} onClose={() => setResOpen(false)} title="Offer a resolution">
        <Select label="Resolution type" value={resType} onChange={setResType} options={RESOLUTION_TYPES} />
        <Input label="Description" rows={3} value={resDesc} onChange={setResDesc}
               placeholder="What are you offering the customer?" />
        {offerResolution.error && (
          <p style={{ color: "var(--danger)", fontSize: 12 }}>{offerResolution.error}</p>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <Btn disabled={!resDesc.trim() || offerResolution.loading}
               onClick={() => offerResolution.execute()}>
            {offerResolution.loading ? "Offering…" : "Offer resolution"}
          </Btn>
          <Btn variant="ghost" onClick={() => setResOpen(false)}>Cancel</Btn>
        </div>
      </Modal>

      <Modal open={propOpen} onClose={() => setPropOpen(false)} title="Propose a settlement">
        <Select label="Proposal type" value={propType} onChange={setPropType} options={PROPOSAL_TYPES} />
        <Input label="Amount (optional)" value={propAmt} onChange={setPropAmt} placeholder="e.g. 75" />
        <Input label="Description" rows={3} value={propDesc} onChange={setPropDesc}
               placeholder="Describe the settlement you are proposing…" />
        {createProposal.error && (
          <p style={{ color: "var(--danger)", fontSize: 12 }}>{createProposal.error}</p>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <Btn disabled={!propDesc.trim() || createProposal.loading}
               onClick={() => createProposal.execute()}>
            {createProposal.loading ? "Proposing…" : "Propose settlement"}
          </Btn>
          <Btn variant="ghost" onClick={() => setPropOpen(false)}>Cancel</Btn>
        </div>
      </Modal>
    </TenantLayout>
  );
}
