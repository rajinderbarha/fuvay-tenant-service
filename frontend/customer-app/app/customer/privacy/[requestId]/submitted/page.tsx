"use client";
/**
 * Shared "Request submitted" receipt for every customer privacy-request type
 * (export, account deletion/erasure, correction, ...). One screen, one
 * presentation resolver (lib/privacy-receipt.ts) — no per-type duplicate
 * screens. Always renders from the canonical detail fetch, never from
 * client-synthesized reference/timestamp/status.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../../components/ErrorBanner";
import { getPrivacyRequest, REQUEST_TYPES, ComplianceRequest } from "../../../../../lib/api/customer-privacy";
import { resolvePrivacyReceiptPresentation, publicReference, requestTypeLabel } from "../../../../../lib/privacy-receipt";

function statusColor(s: string): string {
  if (["completed", "approved"].includes(s)) return "#0a7c3f";
  if (["rejected", "failed", "cancelled"].includes(s)) return "#b91c1c";
  return "#b45309";
}

function fmt(v?: string | null): string {
  if (!v) return "—";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

export default function PrivacyRequestSubmittedPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.requestId as string;

  const [req, setReq] = useState<ComplianceRequest | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    getPrivacyRequest(requestId).then(setReq).catch(setError);
  }, [requestId]);
  useEffect(() => { load(); }, [load]);

  function goToDetails() { router.push(`/customer/privacy/${requestId}`); }
  function goToPrivacyRoot() { router.replace("/customer/privacy"); }

  const presentation = req ? resolvePrivacyReceiptPresentation(req.request_type) : null;
  const ref = req ? publicReference(req) : null;

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 0" }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Request submitted</h1>
        <button aria-label="Close" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44 }}
          onClick={goToPrivacyRoot}>×</button>
      </div>
      <ErrorBanner error={error} />

      {!req ? (
        !error && <div className="co-card">Loading…</div>
      ) : (
        <>
          <div style={{ textAlign: "center", padding: "12px 0 20px" }}
            role="status" aria-live="polite">
            <div style={{
              width: 72, height: 72, margin: "0 auto 16px", borderRadius: "50%",
              background: "rgba(234,88,12,0.12)", display: "flex", alignItems: "center", justifyContent: "center",
            }} aria-hidden="true">
              <span style={{ fontSize: 28 }}>🛡️</span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>{presentation!.headline}</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: 12 }}>{presentation!.message}</p>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px",
              borderRadius: 999, background: "#ecfdf3", color: "#0a7c3f", fontSize: 13, fontWeight: 600,
            }}>
              ✓ {req.status_label ?? req.status ?? "Submitted"}
            </span>
          </div>

          <div className="co-card" role="group" aria-label="Request summary" style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Request summary</div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
              <span>Request type</span>
              <span style={{ fontWeight: 600 }}>{requestTypeLabel(req.request_type, REQUEST_TYPES)}</span>
            </div>
            {ref && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
                <span>Reference</span>
                <span style={{ fontWeight: 600 }}>{ref}</span>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
              <span>Submitted</span>
              <span style={{ fontWeight: 600 }}>{fmt(req.submitted_at)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
              <span>Current status</span>
              <span style={{ fontWeight: 600, color: statusColor(req.status) }}>
                {req.status_label ?? req.status}
              </span>
            </div>
          </div>

          <div className="co-card" style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>What happens next</div>
            {presentation!.nextSteps.map((step, i) => (
              <div key={step} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "6px 0" }}>
                <span style={{
                  width: 22, height: 22, borderRadius: "50%", border: "1px solid var(--border-strong)",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0,
                }} aria-hidden="true">{i + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>

          {presentation!.showAccountActiveNote && (
            <div className="co-card" style={{
              marginBottom: 16, background: "rgba(234,88,12,0.08)", border: "1px solid rgba(234,88,12,0.3)",
            }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>You&apos;re still signed in</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Submitting this request does not immediately delete your account.
              </div>
            </div>
          )}

          <button className="co-btn-primary" style={{ width: "100%", marginBottom: 10 }}
            onClick={goToDetails}>View request</button>
          <button className="co-btn-secondary" style={{ width: "100%" }}
            onClick={goToPrivacyRoot}>Back to Privacy &amp; data</button>
        </>
      )}
    </div>
  );
}
