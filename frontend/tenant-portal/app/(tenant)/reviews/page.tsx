"use client";
/**
 * Reviews — 100% connected to reviewsApi.
 * PROVEN: reply calls reviewsApi.reply() — ONE reply per review enforced.
 * PROVEN: button disabled after reply (has_reply flag from API).
 */
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Skeleton, SectionHeader, StarRating } from "../../../components/shared/ui";
import { reviewsApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { Review } from "../../../lib/api";
import { RefreshCw, Star, CheckCircle2 } from "lucide-react";

export default function ReviewsPage() {
  const [replyModal, setReplyModal] = useState(false);
  const [replyId,    setReplyId]    = useState("");
  const [replyText,  setReplyText]  = useState("");

  const reviews   = useApi(useCallback(() => reviewsApi.list({ limit:"30" }), []));
  const aggregate = useApi(useCallback(() => reviewsApi.getAggregate(), []));

  const replyAction = useAction(useCallback(
    (id:string, text:string) => reviewsApi.reply(id, text),
    []
  ));

  async function handleReply() {
    const res = await replyAction.execute(replyId, replyText);
    if (res) { reviews.refetch(); setReplyModal(false); setReplyText(""); }
  }

  const agg = aggregate.data;

  const SIGNALS: Record<string, string> = {
    overall_quality:"Quality", punctuality:"On Time",
    cleanliness:"Cleanliness", value_for_money:"Value",
    communication:"Communication",
  };

  return (
    <TenantLayout activeNav="reviews">
      <SectionHeader
        title="Reviews"
        subtitle={reviews.loading ? "Loading..." : `${(reviews.data?.reviews ?? []).length} reviews`}
        actions={<Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} onClick={() => { reviews.refetch(); aggregate.refetch(); }}/>}
      />

      {/* Aggregate score */}
      {aggregate.loading ? <Skeleton height={100} style={{ borderRadius:14, marginBottom:16 }}/> : agg && (
        <Card padding={20} style={{ marginBottom:16 }}>
          <div style={{ display:"grid", gridTemplateColumns:"auto 1fr auto", gap:20, alignItems:"center" }}>
            <div style={{ textAlign:"center" }}>
              <p style={{ fontSize:48, fontWeight:800, color:"var(--text-primary)", margin:0, lineHeight:1 }}>
                {agg.avg_composite.toFixed(1)}
              </p>
              <StarRating score={agg.avg_composite} size={18}/>
              <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"6px 0 0" }}>
                {agg.review_count} reviews
              </p>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(140px,1fr))", gap:10 }}>
              {Object.entries(SIGNALS).map(([key, label]) => {
                const score = agg.signal_averages?.[key] ?? 0;
                return (
                  <div key={key}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                      <span style={{ fontSize:11, color:"var(--text-secondary)" }}>{label}</span>
                      <span style={{ fontSize:11, fontWeight:600, color:"var(--text-primary)" }}>
                        {score.toFixed(1)}
                      </span>
                    </div>
                    <div style={{ height:5, background:"var(--border)", borderRadius:999, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${(score/5)*100}%`,
                        background:"#F59E0B", borderRadius:999 }}/>
                    </div>
                  </div>
                );
              })}
            </div>
            <div style={{ textAlign:"center", padding:"12px 16px", borderRadius:12,
              background:"var(--success-bg)", border:"1px solid var(--success-border)" }}>
              <p style={{ fontSize:11, color:"var(--success-text)", margin:"0 0 4px", fontWeight:600 }}>
                REPLY RATE
              </p>
              <p style={{ fontSize:24, fontWeight:700, color:"var(--success-text)", margin:0 }}>
                {agg.reply_rate.toFixed(0)}%
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Review list */}
      {reviews.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={120} style={{ borderRadius:14 }}/>)}
        </div>
      ) : (reviews.data?.reviews ?? []).length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <Star size={32} style={{ marginBottom:12, color:"var(--text-tertiary)" }}/>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>No reviews yet</p>
        </Card>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {(reviews.data?.reviews ?? []).map((rev: Review) => (
            <Card key={rev.review_id} padding={18}>
              <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:12 }}>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                    <StarRating score={rev.composite_score}/>
                    <span style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)" }}>
                      {rev.composite_score.toFixed(1)}
                    </span>
                    <Badge variant={rev.status==="published"?"success":rev.status==="flagged"?"warning":"muted"} size="sm">
                      {rev.status}
                    </Badge>
                    <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>
                      {new Date(rev.created_at).toLocaleDateString("en-IN")}
                    </span>
                  </div>
                  {rev.comment && (
                    <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 10px",
                      lineHeight:1.5, fontStyle:"italic" }}>
                      &ldquo;{rev.comment}&rdquo;
                    </p>
                  )}
                  {/* Signals mini-breakdown */}
                  <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                    {Object.entries(rev.signals ?? {}).map(([k, v]) => (
                      <span key={k} style={{ display:"flex", alignItems:"center", gap:4,
                        padding:"3px 8px", borderRadius:999, fontSize:10, fontWeight:600,
                        background:"var(--surface-sunken)", color:"var(--text-tertiary)" }}>
                        {SIGNALS[k] ?? k}: {String(v)}/5
                      </span>
                    ))}
                  </div>
                  {rev.has_reply && (
                    <div style={{ marginTop:10, padding:"10px 14px", borderRadius:9,
                      background:"var(--info-bg)", border:"1px solid var(--info-border)" }}>
                      <p style={{ fontSize:11, fontWeight:600, color:"var(--info-text)", margin:"0 0 4px" }}>
                        Your reply:
                      </p>
                      <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                        {rev.reply_text}
                      </p>
                    </div>
                  )}
                </div>
                <div style={{ flexShrink:0 }}>
                  {!rev.has_reply ? (
                    <Btn variant="secondary" size="sm"
                      onClick={() => { setReplyId(rev.review_id); setReplyModal(true); }}>
                      Reply
                    </Btn>
                  ) : (
                    <Btn variant="ghost" size="sm" icon={<CheckCircle2 size={14}/>} disabled>Replied</Btn>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={replyModal} onClose={() => setReplyModal(false)} title="Reply to Review">
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--warning-bg)",
            border:"1px solid var(--warning-border)" }}>
            <p style={{ fontSize:12, color:"var(--warning-text)", margin:0 }}>
              You can only reply once. This cannot be edited after submission.
            </p>
          </div>
          {replyAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{replyAction.error}</p>
            </div>
          )}
          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:5 }}>
              Your reply
            </label>
            <textarea value={replyText} onChange={e => setReplyText(e.target.value)}
              placeholder="Thank you for your feedback..."
              rows={4} style={{ width:"100%", padding:12, fontSize:14, fontFamily:"inherit",
                background:"var(--surface)", border:"1px solid var(--border)",
                borderRadius:10, color:"var(--text-primary)", outline:"none",
                resize:"vertical", boxSizing:"border-box" as const }}
              onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
              onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
            />
          </div>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setReplyModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={replyAction.loading} onClick={handleReply}>
              Post Reply
            </Btn>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}
