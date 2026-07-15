"use client";
/**
 * MODULE-L5-17 — Customer Credits (wallet).
 *
 * Shows the service-credit balance the customer holds (from dispute settlements /
 * refunds) and the individual credits with their source and expiry. Wired to the
 * customer_credits engine (/v1/me/credits).
 */
import { useEffect, useState, useCallback } from "react";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  getCreditSummary, listMyCredits, CreditSummary, Credit,
} from "../../../lib/api/customer-credits";

const STATUS_LABEL: Record<string, string> = {
  active: "Active", used: "Used", expired: "Expired", cancelled: "Cancelled",
};
function statusColor(s: string): string {
  if (s === "active") return "#0a7c3f";
  if (s === "used") return "#1d4ed8";
  return "#8a8a8a";
}
const SOURCE_LABEL: Record<string, string> = {
  dispute_settlement: "Dispute settlement", refund: "Refund",
  goodwill: "Goodwill", promotion: "Promotion", manual: "Adjustment",
};

export default function CustomerCreditsPage() {
  const [summary, setSummary] = useState<CreditSummary | null>(null);
  const [credits, setCredits] = useState<Credit[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    getCreditSummary().then(setSummary).catch(setError);
    listMyCredits().then(setCredits).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load]);

  const ccy = credits?.[0]?.currency ?? "₹";

  return (
    <div className="co-container">
      <h1 style={{ fontSize: 20, fontWeight: 700, padding: "12px 0" }}>My Credits</h1>
      <ErrorBanner error={error} />

      {/* Balance card */}
      <div className="co-card" style={{ marginBottom: 16, textAlign: "center",
        background: "linear-gradient(135deg, var(--accent) 0%, #0b6b57 100%)", color: "#fff" }}>
        <div style={{ fontSize: 13, opacity: 0.9 }}>Available balance</div>
        <div style={{ fontSize: 36, fontWeight: 800, margin: "4px 0" }}>
          {ccy}{(summary?.active_credit_balance ?? 0).toLocaleString()}
        </div>
        <div style={{ fontSize: 12, opacity: 0.9 }}>
          {summary?.active_credits ?? 0} active · use at checkout on your next booking
        </div>
      </div>

      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>History</h2>
      {credits === null ? (
        <div className="co-card">Loading…</div>
      ) : credits.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)" }}>
          You have no credits yet. Credits from settlements or refunds appear here.
        </div>
      ) : (
        credits.map((c) => (
          <div key={c.id} className="co-card" style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 17 }}>
                {c.currency}{Number(c.remaining_amount).toLocaleString()}
                {Number(c.remaining_amount) !== Number(c.amount) && (
                  <span style={{ fontSize: 12, fontWeight: 400, color: "var(--text-tertiary)" }}>
                    {" "}of {c.currency}{Number(c.amount).toLocaleString()}
                  </span>
                )}
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(c.status) }}>
                {STATUS_LABEL[c.status] ?? c.status}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
              {SOURCE_LABEL[c.source] ?? c.source}
              {c.customer_message ? ` — ${c.customer_message}` : c.issued_reason ? ` — ${c.issued_reason}` : ""}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 3 }}>
              #{c.credit_number}
              {c.expires_at ? ` · expires ${new Date(c.expires_at).toLocaleDateString()}` : ""}
            </div>
          </div>
        ))
      )}

      <BottomNav />
    </div>
  );
}
