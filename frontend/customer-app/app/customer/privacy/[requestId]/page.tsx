"use client";
/**
 * Canonical Privacy Request detail — the "View request" destination for
 * every request type (export, deletion/erasure, correction, ...). Not
 * duplicated per request type.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../components/ErrorBanner";
import { getPrivacyRequest, REQUEST_TYPES, ComplianceRequest } from "../../../../lib/api/customer-privacy";
import { publicReference, requestTypeLabel } from "../../../../lib/privacy-receipt";

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

export default function PrivacyRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.requestId as string;

  const [req, setReq] = useState<ComplianceRequest | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    getPrivacyRequest(requestId).then(setReq).catch(setError);
  }, [requestId]);
  useEffect(() => { load(); }, [load]);

  const ref = req ? publicReference(req) : null;

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 0" }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Request details</h1>
        <button aria-label="Close" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44 }}
          onClick={() => router.push("/customer/privacy")}>×</button>
      </div>
      <ErrorBanner error={error} />

      {!req ? (
        !error && <div className="co-card">Loading…</div>
      ) : (
        <div className="co-card" role="group" aria-label="Request summary">
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
      )}

      <button className="co-btn-secondary" style={{ width: "100%", marginTop: 16 }}
        onClick={() => router.push("/customer/privacy")}>Back to Privacy &amp; data</button>
    </div>
  );
}
