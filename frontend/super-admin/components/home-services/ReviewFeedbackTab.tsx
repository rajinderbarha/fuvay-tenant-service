"use client";
import React, { useCallback } from "react";
import { Card, Badge, Btn } from "../shared/ui";
import { hsReviewApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";
import { Star, ShieldCheck, CheckCircle2, XCircle } from "lucide-react";

// REVIEW-CONSOLIDATION: Home Services Job 360 -> Review & Feedback tab.
// Resolves the exact canonical ServiceJob's review via the vertical-scoped
// review router (hardcoded to "home-services", never a client-supplied
// vertical or an arbitrary review id unrelated to this job).

const VERTICAL = "home-services";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{value ?? "—"}</div>
    </div>
  );
}

function Stars({ value }: { value: number | null | undefined }) {
  if (value == null) return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star key={i} size={14} fill={i < value ? "var(--warning-text, #eab308)" : "none"}
          color={i < value ? "var(--warning-text, #eab308)" : "var(--border)"} />
      ))}
      <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: 4 }}>{value.toFixed ? value.toFixed(1) : value}</span>
    </span>
  );
}

export function ReviewFeedbackTab({ jobId, jobStatus }: { jobId: string; jobStatus: string }) {
  const review = useApi(useCallback(() => hsReviewApi.getJobReview(VERTICAL, jobId), [jobId]));
  const integrity = useApi(useCallback(() => hsReviewApi.getJobReviewIntegrity(VERTICAL, jobId), [jobId]));
  const lifecycle = useApi(useCallback(() => hsReviewApi.getJobReviewLifecycle(VERTICAL, jobId), [jobId]));
  const ratingImpact = useApi(useCallback(() => hsReviewApi.getJobReviewRatingImpact(VERTICAL, jobId), [jobId]));

  if (review.error) {
    return (
      <Card>
        <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
          Review unavailable due to an error: {review.error}
          {review.requestId && ` (Request ID: ${review.requestId})`}
        </p>
        <Btn variant="ghost" size="sm" onClick={review.refetch}>Retry</Btn>
      </Card>
    );
  }
  if (review.loading) {
    return <Card><p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading review…</p></Card>;
  }

  const d = review.data as Record<string, unknown> | null;
  const state = d?.state as string | undefined;

  if (state === "job_not_completed") {
    return (
      <Card>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Customer review becomes available after the job is completed.
        </p>
      </Card>
    );
  }

  if (state === "awaiting_review") {
    return (
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Badge variant="warning">Awaiting customer review</Badge>
        </div>
        <Field label="Eligible customer" value={(d?.eligible_customer_id as string) ?? "—"} />
        <Field label="Submission window" value={(d?.submission_window as string) ?? "Not configured for this policy"} />
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 10 }}>
          A Super Admin cannot submit a review on behalf of the customer.
        </p>
      </Card>
    );
  }

  if (state === "review_removed") {
    return <Card><p style={{ fontSize: 13, color: "var(--text-secondary)" }}>This review has been removed from public display.</p></Card>;
  }

  // review_available / review_hidden / review_under_moderation
  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
      <div>
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
            <div>
              <Stars value={d?.overall_rating as number} />
              <p style={{ fontSize: 13, fontWeight: 600, margin: "6px 0 2px" }}>{(d?.review_title as string) ?? ""}</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{(d?.review_text as string) ?? "No written review."}</p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
              <Badge variant={state === "review_hidden" ? "danger" : state === "review_under_moderation" ? "warning" : "success"}>
                {state === "review_hidden" ? "Hidden" : state === "review_under_moderation" ? "Under moderation" : "Verified completed job"}
              </Badge>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {d?.submitted_at ? new Date(d.submitted_at as string).toLocaleString() : "—"}
              </span>
            </div>
          </div>
          {Array.isArray(d?.media_urls) && (d!.media_urls as string[]).length > 0 && (
            <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
              {(d!.media_urls as string[]).map((u, i) => (
                <img key={i} src={u} alt="review upload" style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 6, border: "1px solid var(--border)" }} />
              ))}
            </div>
          )}
          {Array.isArray(d?.review_tags) && (d!.review_tags as string[]).length > 0 && (
            <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
              {(d!.review_tags as string[]).map((t, i) => <Badge key={i} variant="muted" size="sm">{t}</Badge>)}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, marginTop: 8 }}>
            <Field label="Service quality" value={<Stars value={d?.quality_rating as number} />} />
            <Field label="Technician behaviour" value={<Stars value={d?.communication_rating as number} />} />
            <Field label="Timeliness" value={<Stars value={d?.punctuality_rating as number} />} />
            <Field label="Value for money" value={<Stars value={d?.value_rating as number} />} />
          </div>
          {d?.edited_at ? <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>Edited {new Date(d.edited_at as string).toLocaleString()}</p> : null}
        </Card>

        <Card style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Provider response</p>
          {d?.reply ? (
            <>
              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{(d.reply as Record<string, unknown>).reply_text as string}</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                Status: {(d.reply as Record<string, unknown>).status as string} · {(d.reply as Record<string, unknown>).submitted_at
                  ? new Date((d.reply as Record<string, unknown>).submitted_at as string).toLocaleString() : "—"}
              </p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>
                Provider-authored response. Immutable except through the audited provider workflow.
              </p>
            </>
          ) : (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No provider response yet.</p>
          )}
        </Card>

        <Card>
          <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Review lifecycle</p>
          {(lifecycle.data?.events.length ?? 0) === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No lifecycle events recorded yet.</p>
          ) : lifecycle.data!.events.map((e, i) => (
            <div key={i} style={{ display: "flex", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
              <span style={{ color: "var(--text-tertiary)", minWidth: 140 }}>
                {(e as Record<string, unknown>).created_at ? new Date((e as Record<string, unknown>).created_at as string).toLocaleString() : "—"}
              </span>
              <span>{(e as Record<string, unknown>).event_type as string} — {(e as Record<string, unknown>).actor_type as string}</span>
            </div>
          ))}
        </Card>
      </div>

      <div>
        <Card style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}>
            <ShieldCheck size={14} /> Review integrity &amp; moderation
          </p>
          {integrity.data && (
            <>
              {Object.entries(integrity.data.checks).filter(([, v]) => v !== null).map(([k, v]) => (
                <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginBottom: 5, color: "var(--text-secondary)" }}>
                  {v ? <CheckCircle2 size={13} style={{ color: "var(--success-text)" }} /> : <XCircle size={13} style={{ color: "var(--danger-text)" }} />}
                  {k.replace(/_/g, " ")}
                </div>
              ))}
              <div style={{ marginTop: 8 }}>
                <Badge variant={integrity.data.status === "no_action_required" ? "success" : "warning"}>
                  {integrity.data.status === "no_action_required" ? "No action required" : `Moderation required (${integrity.data.reason_code})`}
                </Badge>
              </div>
            </>
          )}
        </Card>

        <Card style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Rating impact</p>
          {ratingImpact.data && (
            <>
              <Field label="Provider rating" value={`${ratingImpact.data.provider_rating_current} (${ratingImpact.data.provider_review_count} reviews)`} />
              {ratingImpact.data.staff_rating_current != null && (
                <Field label="Staff rating" value={`${ratingImpact.data.staff_rating_current} (${ratingImpact.data.staff_completed_job_count} reviews)`} />
              )}
              <Field label="Contributes to rating" value={ratingImpact.data.contributes ? "Yes" : "No"} />
              {!ratingImpact.data.contributes && <Field label="Reason excluded" value={ratingImpact.data.excluded_reason as string} />}
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>This panel is informational only.</p>
            </>
          )}
        </Card>

        <Card>
          <p style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-tertiary)", margin: "0 0 10px" }}>Payment context</p>
          <p style={{ fontSize: 11, color: "var(--info-text, #0f6b60)", marginBottom: 8 }}>Customer pays the provider directly. Fuvay records payment confirmation only.</p>
          <Field label="Platform collection" value="₹0" />
        </Card>
      </div>
    </div>
  );
}
