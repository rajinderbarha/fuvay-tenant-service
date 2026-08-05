"use client";
// REVIEW-CONSOLIDATION: Home Services Review Moderation -- an exception-
// only queue over the SAME canonical customer_reviews engine (flagged,
// hidden, rejected, deleted reviews for Home Services only). Normal
// published reviews never appear here; they live on the Job 360 Review tab.
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal } from "../../../../../components/shared/ui";
import { hsReviewApi } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { ExternalLink } from "lucide-react";

const VERTICAL = "home-services";

function SummaryCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Card style={{ padding: 14 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{label}</div>
    </Card>
  );
}

export default function HomeServicesReviewModerationPage() {
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);

  const summary = useApi(useCallback(() => hsReviewApi.moderationSummary(VERTICAL), []));
  const queue = useApi(useCallback(() => hsReviewApi.listModerationQueue(VERTICAL, { status, page_size: 50 }), [status]));

  const rows = (queue.data?.items ?? []) as Record<string, unknown>[];
  const s = summary.data;

  return (
    <AdminLayout>
      <div style={{ padding: "0 4px" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Home Services / Reviews Moderation</p>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>Review Moderation</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          Exception queue only — flagged, reported, hidden or removed Home Services reviews. Normal published
          reviews live on each job&apos;s Review &amp; Feedback tab, not here.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10, marginBottom: 16 }}>
          <SummaryCard label="Pending Review" value={s?.pending_review ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Flagged" value={s?.flagged ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Reported" value={s?.reported ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Suspicious" value={s?.suspicious ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Under Appeal" value={s?.under_appeal ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Hidden" value={s?.hidden ?? (summary.error ? "—" : 0)} />
          <SummaryCard label="Resolved" value={s?.resolved ?? (summary.error ? "—" : 0)} />
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {[undefined, "flagged", "hidden", "rejected", "deleted"].map(st => (
            <Btn key={st ?? "all"} variant={status === st ? "primary" : "ghost"} onClick={() => setStatus(st)}>{st ?? "All exceptions"}</Btn>
          ))}
        </div>

        <Card style={{ padding: 0 }}>
          {queue.error ? (
            <div style={{ padding: 24, textAlign: "center" }}>
              <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{queue.error}</p>
              <Btn variant="ghost" size="sm" onClick={queue.refetch}>Retry</Btn>
            </div>
          ) : queue.loading ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
          ) : rows.length === 0 ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
              No reviews currently require moderation.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                    {["Rating", "Excerpt", "Provider", "Status", "Reports", "Created", ""].map(h => (
                      <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(rv => (
                    <tr key={rv.id as string} onClick={() => setSelected(rv)} style={{ borderBottom: "1px solid var(--border)", cursor: "pointer" }}>
                      <td style={{ padding: "9px 14px" }}>{String(rv.overall_rating)}★</td>
                      <td style={{ padding: "9px 14px", maxWidth: 280 }}>{String(rv.review_text ?? "").slice(0, 80) || "—"}</td>
                      <td style={{ padding: "9px 14px" }}>{rv.tenant_name as string}</td>
                      <td style={{ padding: "9px 14px" }}><Badge variant={rv.status === "hidden" || rv.status === "deleted" ? "danger" : "warning"} size="sm">{rv.status as string}</Badge></td>
                      <td style={{ padding: "9px 14px" }}>{String(rv.report_count ?? 0)}</td>
                      <td style={{ padding: "9px 14px", color: "var(--text-tertiary)" }}>{rv.created_at ? new Date(rv.created_at as string).toLocaleDateString() : "—"}</td>
                      <td style={{ padding: "9px 14px" }}>
                        <a href={`/admin/home-services/service-jobs/${rv.job_id}?tab=review`} target="_blank" rel="noreferrer"
                          style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--brand)" }}
                          onClick={e => e.stopPropagation()}>
                          Open Job 360° <ExternalLink size={11}/>
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Review Inspector" size="lg">
        {selected && <ReviewInspector review={selected} onChanged={() => { queue.refetch(); summary.refetch(); setSelected(null); }} />}
      </Modal>
    </AdminLayout>
  );
}

function ReviewInspector({ review, onChanged }: { review: Record<string, unknown>; onChanged: () => void }) {
  const [reason, setReason] = useState("");
  const hide = useAction((r: string) => hsReviewApi.moderationHide(VERTICAL, review.id as string, r));
  const restore = useAction((r: string) => hsReviewApi.moderationRestore(VERTICAL, review.id as string, r));
  const resolve = useAction((r: string) => hsReviewApi.moderationResolve(VERTICAL, review.id as string, r));
  const escalate = useAction((r: string) => hsReviewApi.moderationEscalate(VERTICAL, review.id as string, r));

  async function run(action: { execute: (r: string) => Promise<unknown> }) {
    const res = await action.execute(reason);
    if (res) { setReason(""); onChanged(); }
  }

  return (
    <div>
      <p style={{ fontSize: 13, fontWeight: 700 }}>{String(review.overall_rating)}★ — {review.tenant_name as string}</p>
      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{review.review_text as string}</p>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Status: {review.status as string}</p>
      <textarea placeholder="Reason" value={reason} onChange={e => setReason(e.target.value)} rows={2}
        style={{ width: "100%", padding: "6px 8px", margin: "10px 0", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 12, boxSizing: "border-box" }} />
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <Btn variant="danger" size="sm" onClick={() => run(hide)} disabled={hide.loading}>Hide</Btn>
        <Btn variant="success" size="sm" onClick={() => run(restore)} disabled={restore.loading}>Restore</Btn>
        <Btn variant="secondary" size="sm" onClick={() => run(resolve)} disabled={resolve.loading}>Resolve Report</Btn>
        <Btn variant="warning" size="sm" onClick={() => run(escalate)} disabled={escalate.loading}>Escalate</Btn>
        <a href={`/admin/home-services/service-jobs/${review.job_id}?tab=review`} target="_blank" rel="noreferrer">
          <Btn variant="ghost" size="sm">Open Job 360°</Btn>
        </a>
      </div>
    </div>
  );
}
