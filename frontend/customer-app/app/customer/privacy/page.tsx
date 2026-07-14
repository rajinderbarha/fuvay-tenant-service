"use client";
/**
 * MODULE-L5-15 — Customer Privacy & Data Rights.
 *
 * Lets a customer exercise its data rights (export / erasure / correction /
 * consent withdrawal / grievance) and see the status of past requests. Wired to
 * the compliance customer self-service engine (/v1/me/compliance).
 */
import { useEffect, useState, useCallback } from "react";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  listPrivacyRequests, createPrivacyRequest, listMyConsents, withdrawConsent,
  REQUEST_TYPES, ComplianceRequest, ConsentRecord,
} from "../../../lib/api/customer-privacy";

function statusColor(s: string): string {
  if (["completed", "approved"].includes(s)) return "#0a7c3f";
  if (["rejected", "failed", "cancelled"].includes(s)) return "#b91c1c";
  return "#b45309";
}

export default function CustomerPrivacyPage() {
  const [requests, setRequests] = useState<ComplianceRequest[] | null>(null);
  const [consents, setConsents] = useState<ConsentRecord[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ok, setOk] = useState<string | null>(null);

  const [type, setType] = useState(REQUEST_TYPES[0].value);
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    listPrivacyRequests().then(setRequests).catch(setError);
    listMyConsents().then(setConsents).catch(() => setConsents([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const selected = REQUEST_TYPES.find((t) => t.value === type);
  const needsReason = !!selected?.needsReason;
  const canSubmit = confirm && (!needsReason || reason.trim().length > 0) && !busy;

  async function submit() {
    setBusy(true); setError(null); setOk(null);
    try {
      const res = await createPrivacyRequest(type, reason.trim());
      setOk(res.message ?? "Your request has been submitted.");
      setReason(""); setConfirm(false);
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  async function doWithdraw(ct: string) {
    setBusy(true); setError(null); setOk(null);
    try {
      await withdrawConsent(ct, "Withdrawn from app");
      setOk("Consent withdrawn.");
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>Privacy &amp; Data</h1>
      <ErrorBanner error={error} />
      {ok && (
        <div className="co-card" style={{ background: "#ecfdf3", color: "#0a7c3f", marginBottom: 12 }}>{ok}</div>
      )}

      {/* New request */}
      <div className="co-card" style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Make a data request</div>
        <select value={type} onChange={(e) => setType(e.target.value)}
          style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)",
            fontSize: 15, marginBottom: 10 }}>
          {REQUEST_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        {needsReason && (
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
            placeholder="Please tell us why (required)"
            style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)",
              fontSize: 15, marginBottom: 10 }} />
        )}
        <label style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 13,
          color: "var(--text-secondary)", marginBottom: 12 }}>
          <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)}
            style={{ marginTop: 2 }} />
          I understand this request will be processed under applicable data-protection law and may
          take up to 72 hours.
        </label>
        <button className="co-btn-primary" disabled={!canSubmit} onClick={submit}
          style={{ width: "100%" }}>{busy ? "Submitting…" : "Submit request"}</button>
      </div>

      {/* Consents */}
      {consents && consents.length > 0 && (
        <>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>My consents</h2>
          {consents.map((c) => (
            <div key={c.consent_type} className="co-card" style={{ marginBottom: 8,
              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{c.consent_type.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{c.status}</div>
              </div>
              {c.status === "granted" && (
                <button className="co-btn-secondary" style={{ fontSize: 13, padding: "6px 12px" }}
                  disabled={busy} onClick={() => doWithdraw(c.consent_type)}>Withdraw</button>
              )}
            </div>
          ))}
        </>
      )}

      {/* Past requests */}
      <h2 style={{ fontSize: 16, fontWeight: 700, margin: "16px 0 8px" }}>My requests</h2>
      {requests === null ? (
        <div className="co-card">Loading…</div>
      ) : requests.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>
          No requests yet.
        </div>
      ) : (
        requests.map((r) => (
          <div key={r.id ?? r.request_number} className="co-card" style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 600 }}>
                {REQUEST_TYPES.find((t) => t.value === r.request_type)?.label ?? r.request_type}
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(r.status) }}>
                {r.status_label ?? r.status}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 3 }}>
              #{r.request_number}{r.due_at ? ` · due ${new Date(r.due_at).toLocaleDateString()}` : ""}
            </div>
          </div>
        ))
      )}

      <BottomNav />
    </div>
  );
}
