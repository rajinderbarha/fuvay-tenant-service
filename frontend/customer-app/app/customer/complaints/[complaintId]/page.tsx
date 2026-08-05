"use client";
/**
 * MODULE-L5-02 bug #34 — Customer Complaint detail.
 *
 * This is the customer half of everything repaired this module:
 *   #27 accept / reject a proposed resolution (previously the transition was
 *       impossible, so a proposed resolution stalled forever)
 *   #28 accepting a *rework* resolution now spawns a real rework request
 *   #29 request a refund (the refund path now advances the complaint and
 *       resolves it on verification)
 *   #30 respond to a settlement proposal — which only takes effect once BOTH
 *       the customer and the provider accept
 *   #35 list the offered resolutions at all (the customer had accept/reject
 *       endpoints but no way to SEE what was offered or get its id)
 */
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import BottomNav from "../../../../components/BottomNav";
import ErrorBanner from "../../../../components/ErrorBanner";
import {
  getComplaint, getComplaintMessages, getComplaintResolutions,
  getSettlementProposals, addComplaintMessage, acceptResolution,
  rejectResolution, requestRefund, respondToSettlement, cancelComplaint,
  getAISession, submitAIAnswers,
  Complaint, ComplaintMessage, ComplaintResolution, SettlementProposal, AISession,
} from "../../../../lib/api/customer-complaints";

const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  awaiting_provider_response: "Awaiting provider",
  awaiting_customer_response: "Your response needed",
  under_admin_review: "Under review",
  resolution_proposed: "Resolution offered",
  rework_approved: "Rework scheduled",
  refund_requested: "Refund requested",
  refund_approved: "Refund approved",
  refund_recorded: "Refund paid",
  resolved: "Resolved",
  settled: "Settled",
  closed: "Closed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

const FINAL = ["resolved", "settled", "closed", "rejected", "cancelled"];

export default function CustomerComplaintDetailPage() {
  const params = useParams();
  const id = String(params?.complaintId ?? "");

  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [messages, setMessages] = useState<ComplaintMessage[]>([]);
  const [resolutions, setResolutions] = useState<ComplaintResolution[]>([]);
  const [proposals, setProposals] = useState<SettlementProposal[]>([]);
  const [aiSession, setAiSession] = useState<AISession | null>(null);
  const [aiAnswers, setAiAnswers] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const [reply, setReply] = useState("");
  const [showRefund, setShowRefund] = useState(false);
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");

  const load = useCallback(() => {
    getComplaint(id).then(setComplaint).catch(setError);
    getComplaintMessages(id).then(setMessages).catch(() => {});
    getComplaintResolutions(id).then(setResolutions).catch(() => {});
    getSettlementProposals(id).then(setProposals).catch(() => {});
    getAISession(id).then(s => {
      setAiSession(s);
      if (s?.customer_questions) setAiAnswers(a => a.length ? a : s.customer_questions!.map(() => ""));
    }).catch(() => {});
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true); setActionError(null);
    try { await fn(); load(); }
    catch (e) { setActionError(e); }
    finally { setBusy(false); }
  }

  const status = complaint?.status ?? "";
  const isFinal = FINAL.includes(status);

  return (
    <div className="co-container">
      <div style={{ padding: "10px 0" }}>
        <Link href="/customer/complaints" style={{ fontSize: 13 }}>← My complaints</Link>
      </div>

      <ErrorBanner error={error} />
      {!complaint && !error && <div className="co-skeleton" style={{ height: 180 }} />}

      {complaint && (
        <>
          <div className="co-card" style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ fontWeight: 700 }}>{complaint.complaint_number}</div>
              <span style={{ fontSize: 12, fontWeight: 700 }}>
                {STATUS_LABEL[status] ?? status.replace(/_/g, " ")}
              </span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
              {complaint.title || complaint.complaint_type.replace(/_/g, " ")}
            </div>
            <div style={{ fontSize: 13, color: "#444" }}>{complaint.description}</div>
            <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
              Raised {String(complaint.created_at).slice(0, 10)}
            </div>
          </div>

          <ErrorBanner error={actionError} />

          {/* ── AI settlement questions (bug #34/#37) ── */}
          {aiSession && (aiSession.customer_questions?.length ?? 0) > 0 && (
            <div className="co-card" style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>AI settlement — a few questions</div>
              <div style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>
                An AI mediator is reviewing your complaint. Answer these so it can propose a fair
                outcome. Compensation, if any, is paid in account credit — never cash.
              </div>
              {aiSession.awaiting_your_answers ? (
                <>
                  {(aiSession.customer_questions ?? []).map((q, i) => (
                    <div key={i} style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{q}</div>
                      <textarea
                        rows={2}
                        value={aiAnswers[i] ?? ""}
                        onChange={e => setAiAnswers(a => { const n = [...a]; n[i] = e.target.value; return n; })}
                        style={{ width: "100%", padding: 8, borderRadius: 8 }}
                      />
                    </div>
                  ))}
                  <button
                    className="co-btn"
                    disabled={busy || aiAnswers.some(a => !a.trim())}
                    onClick={() => run(() => submitAIAnswers(id, aiAnswers))}
                  >
                    Submit answers
                  </button>
                </>
              ) : (
                <div style={{ fontSize: 13, color: "#0a7c3f" }}>
                  ✓ Thanks — your answers are in. The AI will propose a settlement once the provider
                  has responded too.
                </div>
              )}
            </div>
          )}

          {/* ── Resolutions offered (bug #35: the customer can finally SEE these) ── */}
          {resolutions.length > 0 && (
            <div className="co-card" style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Resolution offered</div>
              {resolutions.map(r => {
                const pending = r.status === "proposed";
                return (
                  <div key={r.id} style={{
                    padding: 10, border: "1px solid #e5e5e5", borderRadius: 8, marginBottom: 8,
                  }}>
                    <div style={{ fontWeight: 600, marginBottom: 2 }}>
                      {r.resolution_type.replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}>{r.description}</div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: pending ? 8 : 0 }}>
                      {r.status.replace(/_/g, " ")}
                    </div>
                    {r.resolution_type === "rework" && pending && (
                      <div style={{ fontSize: 11, color: "#b45309", marginBottom: 8 }}>
                        Accepting this books a free rework visit.
                      </div>
                    )}
                    {pending && (
                      <div style={{ display: "flex", gap: 8 }}>
                        <button className="co-btn" disabled={busy}
                          onClick={() => run(() => acceptResolution(id, r.id))}>
                          Accept
                        </button>
                        <button className="co-btn co-btn-secondary" disabled={busy}
                          onClick={() => run(() => rejectResolution(id, r.id, "Not acceptable"))}>
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Settlement proposals (bug #30: needs BOTH parties) ── */}
          {proposals.length > 0 && (
            <div className="co-card" style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Settlement</div>
              <div style={{ fontSize: 11, color: "#666", marginBottom: 8 }}>
                A settlement only takes effect once both you and the provider accept it.
              </div>
              {proposals.map(p => {
                const awaitingMe = p.status === "proposed" && !p.customer_response;
                return (
                  <div key={p.id} style={{
                    padding: 10, border: "1px solid #e5e5e5", borderRadius: 8, marginBottom: 8,
                  }}>
                    <div style={{ fontWeight: 600, marginBottom: 2 }}>
                      {p.proposal_type.replace(/_/g, " ")}
                      {p.proposal_amount != null ? ` · ₹${p.proposal_amount}` : ""}
                    </div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}>{p.description}</div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: awaitingMe ? 8 : 0 }}>
                      you: {p.customer_response ?? "—"} · provider: {p.tenant_response ?? "—"} · {p.status}
                    </div>
                    {awaitingMe && (
                      <div style={{ display: "flex", gap: 8 }}>
                        <button className="co-btn" disabled={busy}
                          onClick={() => run(() => respondToSettlement(id, p.id, "accept"))}>
                          Accept
                        </button>
                        <button className="co-btn co-btn-secondary" disabled={busy}
                          onClick={() => run(() => respondToSettlement(id, p.id, "reject"))}>
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Messages ── */}
          <div className="co-card" style={{ marginBottom: 14 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Conversation</div>
            {messages.length === 0 && (
              <div style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>No messages yet.</div>
            )}
            {messages.map(m => (
              <div key={m.id} style={{
                padding: 10, borderRadius: 8, marginBottom: 8,
                background: m.sender_type === "customer" ? "#FFF4E6" : "#f6f6f6",
              }}>
                <div style={{ fontSize: 11, color: "#666", marginBottom: 3 }}>
                  {m.sender_type} · {String(m.created_at).slice(0, 16).replace("T", " ")}
                </div>
                <div style={{ fontSize: 13 }}>{m.message_text}</div>
              </div>
            ))}
            {!isFinal && (
              <>
                <textarea
                  value={reply}
                  onChange={e => setReply(e.target.value)}
                  rows={3}
                  placeholder="Add a message…"
                  style={{ width: "100%", padding: 10, borderRadius: 8, marginTop: 6 }}
                />
                <button className="co-btn" disabled={!reply.trim() || busy}
                  onClick={() => run(async () => {
                    await addComplaintMessage(id, reply.trim());
                    setReply("");
                  })}>
                  Send
                </button>
              </>
            )}
          </div>

          {/* ── Refund request (bug #29) ── */}
          {!isFinal && (
            <div className="co-card" style={{ marginBottom: 14 }}>
              {!showRefund ? (
                <button className="co-btn co-btn-secondary" onClick={() => setShowRefund(true)}>
                  Request a refund
                </button>
              ) : (
                <>
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>Request a refund</div>
                  <input
                    value={refundAmount}
                    onChange={e => setRefundAmount(e.target.value)}
                    placeholder="Amount (₹)"
                    style={{ width: "100%", padding: 10, borderRadius: 8, marginBottom: 8 }}
                  />
                  <textarea
                    value={refundReason}
                    onChange={e => setRefundReason(e.target.value)}
                    rows={3}
                    placeholder="Why are you requesting a refund?"
                    style={{ width: "100%", padding: 10, borderRadius: 8, marginBottom: 8 }}
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="co-btn" disabled={!refundReason.trim() || busy}
                      onClick={() => run(async () => {
                        await requestRefund(id, {
                          refund_type: "partial",
                          reason: refundReason.trim(),
                          ...(refundAmount ? { requested_amount: Number(refundAmount) } : {}),
                        });
                        setShowRefund(false); setRefundAmount(""); setRefundReason("");
                      })}>
                      Submit refund request
                    </button>
                    <button className="co-btn co-btn-secondary" onClick={() => setShowRefund(false)}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Withdraw ── */}
          {!isFinal && (
            <button className="co-btn co-btn-secondary" disabled={busy}
              style={{ marginBottom: 20 }}
              onClick={() => run(() => cancelComplaint(id, "Withdrawn by customer"))}>
              Withdraw complaint
            </button>
          )}
        </>
      )}

      <BottomNav />
    </div>
  );
}
