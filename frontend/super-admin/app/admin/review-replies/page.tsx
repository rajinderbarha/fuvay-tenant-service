"use client";
import { useCallback, useState } from "react";
import { adminReplyApi, type ReviewReplyRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, SectionHeader, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { MessageSquare, RefreshCw, CheckCircle, XCircle } from "lucide-react";

function statusVariant(s: string): "success"|"warning"|"danger" {
  if (s === "approved") return "success";
  if (s === "pending")  return "warning";
  return "danger";
}

export default function AdminReviewRepliesPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const { data, loading, refetch } = useApi(
    useCallback(() => adminReplyApi.list("pending"), [])
  );
  const replies: ReviewReplyRecord[] = (Array.isArray(data) ? data : []) as ReviewReplyRecord[];

  const approveAction = useAction(useCallback((reviewId: string) => adminReplyApi.approve(reviewId), []));
  const rejectAction  = useAction(useCallback((reviewId: string) => adminReplyApi.reject(reviewId, "Policy violation"), []));

  const handleApprove = async (reviewId: string) => {
    const result = await approveAction.execute(reviewId);
    if (result) { addToast("Reply approved.", "success"); refetch(); }
    else { addToast(approveAction.error ?? "Failed.", "danger"); }
  };

  const handleReject = async (reviewId: string) => {
    const result = await rejectAction.execute(reviewId);
    if (result) { addToast("Reply rejected.", "success"); refetch(); }
    else { addToast(rejectAction.error ?? "Failed.", "danger"); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <SectionHeader eyebrow="Trust & quality" title="Provider Replies"
        description="Approve or reject pending provider replies to customer reviews." icon={<MessageSquare />}
        actions={<Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>} />

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0,1,2].map(i => <Skeleton key={i} height={90} />)}
        </div>
      ) : replies.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <MessageSquare size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No pending replies.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {replies.map((rp: ReviewReplyRecord) => (
            <Card key={rp.id} padding={16}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                    <Badge variant={statusVariant(rp.status)}>{rp.status}</Badge>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      Review: {rp.review_id?.slice(0, 8)}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                    {rp.reply_text}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
                    {rp.submitted_at ? new Date(rp.submitted_at).toLocaleString() : "—"}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <Btn size="sm" onClick={() => handleApprove(rp.review_id)} loading={approveAction.loading}>
                    <CheckCircle size={12} /> Approve
                  </Btn>
                  <Btn size="sm" variant="ghost" onClick={() => handleReject(rp.review_id)} loading={rejectAction.loading}>
                    <XCircle size={12} /> Reject
                  </Btn>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
