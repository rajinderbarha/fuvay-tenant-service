"use client";
import React, { useState } from "react";
import { PageHeader, Section, Card, Button } from "@serviceos/design-system";
import { ReadinessTag } from "../widgets/ReadinessTag";

/**
 * Reusable review/approval workspace pattern (UX-02) — a full page, not a
 * small modal. Used by: Verification Review, Compliance Case resolution.
 *
 * Document previews are fixture tokens only, never raw storage keys or
 * signed URLs (per hard constraint) — `renderDocumentPreview` is supplied
 * by the caller and must not leak such values either.
 */
export interface ChecklistItem { id: string; label: string; status: "pending" | "pass" | "fail"; }

export function ReviewApprovalWorkspace({
  title, summary, checklist, documents, onDecision,
}: {
  title: string;
  summary: React.ReactNode;
  checklist: ChecklistItem[];
  documents: { id: string; label: string }[];
  onDecision?: (decision: "approve" | "reject" | "request_more_info", reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | "request_more_info" | null>(null);
  const [confirmed, setConfirmed] = useState<string | null>(null);

  function requestDecision(d: "approve" | "reject" | "request_more_info") {
    setPendingDecision(d);
  }
  function confirm() {
    if (!pendingDecision) return;
    onDecision?.(pendingDecision, reason);
    setConfirmed(`${pendingDecision} recorded (design-only — no backend call in this workspace).`);
    setPendingDecision(null);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <PageHeader title={title} actions={<ReadinessTag readiness="MOCK_DESIGN_ONLY" />} />

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <Card>
            <Section title="Applicant Summary">{summary}</Section>
          </Card>
          <Card>
            <Section title="Checklist">
              <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {checklist.map((c) => (
                  <li key={c.id} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>
                    <span>{c.label}</span>
                    <span style={{
                      color: c.status === "pass" ? "var(--success-text)" : c.status === "fail" ? "var(--danger-text)" : "var(--warning-text)",
                      fontWeight: 600, fontSize: "0.75rem",
                    }}>{c.status.toUpperCase()}</span>
                  </li>
                ))}
              </ul>
            </Section>
          </Card>
          <Card>
            <Section title="Documents (secure preview — no raw storage keys/URLs shown)">
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {documents.map((d) => (
                  <div key={d.id} style={{ padding: "0.75rem", border: "1px dashed var(--border)", borderRadius: "var(--radius-md)", color: "var(--text-secondary)" }}>
                    {d.label} — [secure preview placeholder, token-gated]
                  </div>
                ))}
              </div>
            </Section>
          </Card>
        </div>

        <Card>
          <Section title="Decision">
            <textarea
              aria-label="Decision reason"
              placeholder="Reason (required for reject / request more info)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              style={{ width: "100%", minHeight: "6rem", padding: "0.5rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg-surface)", color: "var(--text-primary)" }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.75rem" }}>
              <Button onClick={() => requestDecision("approve")}>Approve</Button>
              <Button variant="secondary" onClick={() => requestDecision("request_more_info")}>Request More Info</Button>
              <Button variant="destructive" onClick={() => requestDecision("reject")} disabled={!reason}>Reject</Button>
            </div>
            {pendingDecision && (
              <div role="alertdialog" aria-label="Confirm decision" style={{ marginTop: "0.75rem", padding: "0.75rem", border: "1px solid var(--warning-border)", background: "var(--warning-bg)", borderRadius: "var(--radius-md)" }}>
                <p style={{ margin: 0 }}>Confirm: {pendingDecision.replace(/_/g, " ")}?</p>
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <Button size="sm" onClick={confirm}>Confirm</Button>
                  <Button size="sm" variant="ghost" onClick={() => setPendingDecision(null)}>Cancel</Button>
                </div>
              </div>
            )}
            {confirmed && <p style={{ marginTop: "0.75rem", color: "var(--success-text)" }}>{confirmed}</p>}
          </Section>
        </Card>
      </div>
    </div>
  );
}
