"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../lib/api";

type LegalDocument = {
  id: string;
  doc_type: string;
  title: string;
  version: string;
  summary?: string | null;
};

type ConsentStatus = {
  requires_acceptance: boolean;
  documents: LegalDocument[];
  document_ids: string[];
  message: string;
};

export function LegalReacceptanceGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setStatus(await apiFetch<ConsentStatus>("/v1/legal/consent-status"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not check the updated terms.");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function acceptUpdates() {
    if (!status || !accepted) return;
    setBusy(true);
    setError(null);
    try {
      const next = await apiFetch<ConsentStatus>("/v1/legal/accept", {
        method: "POST",
        body: JSON.stringify({ accepted: true, document_ids: status.document_ids }),
      });
      setStatus(next);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The acceptance could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !status) {
    return (
      <div style={{ maxWidth: 560, margin: "80px auto", padding: 24, textAlign: "center" }}>
        <h1 style={{ fontSize: 20, marginBottom: 8 }}>We couldn&apos;t check the updated terms</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: 18 }}>{error}</p>
        <button type="button" onClick={() => void load()} style={{ padding: "10px 18px", cursor: "pointer" }}>Try again</button>
      </div>
    );
  }
  if (!status) {
    return <div style={{ padding: 32, color: "var(--text-secondary)" }}>Checking updated terms…</div>;
  }
  if (!status.requires_acceptance) return <>{children}</>;

  return (
    <main style={{ maxWidth: 680, margin: "48px auto", padding: "0 20px" }}>
      <section style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 28 }}>
        <p style={{ color: "var(--brand)", fontWeight: 700, fontSize: 12, letterSpacing: ".06em", textTransform: "uppercase" }}>Action required</p>
        <h1 style={{ fontSize: 26, margin: "6px 0 10px" }}>Review our updated provider terms</h1>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{status.message}</p>
        <ul style={{ lineHeight: 1.7, paddingLeft: 20 }}>
          <li>Your business is responsible for technician screening, supervision, and field work.</li>
          <li>Warranty, complaint, refund, and settlement decisions are handled directly with the customer.</li>
          <li>Missed response SLAs may deduct usage credits and affect account health.</li>
          <li>Fuvay does not hold a provider security deposit or adjudicate the case.</li>
        </ul>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, margin: "18px 0" }}>
          {status.documents.map(document => (
            <Link key={document.id} href={document.doc_type === "privacy_policy" ? "/privacy" : "/terms"} target="_blank"
              style={{ color: "var(--brand)", fontWeight: 650 }}>
              Read {document.title} (v{document.version})
            </Link>
          ))}
        </div>
        <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 14, background: "var(--surface-sunken)", borderRadius: 10, cursor: "pointer" }}>
          <input type="checkbox" checked={accepted} onChange={event => setAccepted(event.target.checked)} style={{ marginTop: 3 }} />
          <span>I have read and accept the updated terms for this provider workspace.</span>
        </label>
        {error && <p role="alert" style={{ color: "var(--danger-text)", marginBottom: 0 }}>{error}</p>}
        <button type="button" disabled={!accepted || busy} onClick={() => void acceptUpdates()}
          style={{ width: "100%", marginTop: 18, padding: "12px 18px", border: 0, borderRadius: 9, background: "var(--brand)", color: "white", fontWeight: 700, cursor: accepted && !busy ? "pointer" : "not-allowed", opacity: accepted && !busy ? 1 : .55 }}>
          {busy ? "Saving acceptance…" : "Accept and continue"}
        </button>
      </section>
    </main>
  );
}
