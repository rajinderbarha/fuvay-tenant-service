"use client";
/**
 * MODULE-L5-17 — Service Credits.
 *
 * Named "Service credits" (not "Rewards & credits") — no rewards, referral,
 * cashback, or loyalty capability exists anywhere in this backend (the
 * loyalty engine is an unmounted stub with zero models), so this only ever
 * shows the real customer_credits engine (/v1/me/credits): the service
 * credit balance issued from dispute settlements/refunds, and its history.
 * Balance is the backend's own SUM(remaining_amount), never computed here.
 */
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import BottomNav from "../../../components/BottomNav";
import ErrorBanner from "../../../components/ErrorBanner";
import {
  getCreditSummary, listMyCredits, CreditSummary, Credit,
} from "../../../lib/api/customer-credits";

const SOURCE_LABEL: Record<string, string> = {
  dispute_settlement: "Dispute settlement credit",
  refund: "Refund",
  goodwill: "Customer care credit",
  promotion: "Promotion credit",
  manual: "Service adjustment",
};

function fmtDate(v?: string | null): string {
  if (!v) return "";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export default function CustomerCreditsPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<CreditSummary | null>(null);
  const [credits, setCredits] = useState<Credit[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(() => {
    getCreditSummary().then(setSummary).catch(setError);
    listMyCredits().then(setCredits).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load]);

  const ccy = credits?.[0]?.currency ?? "₹";
  const visibleCredits = credits ? (showAll ? credits : credits.slice(0, 2)) : null;

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0" }}>
        <button aria-label="Back" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44, padding: 0 }}
          onClick={() => router.back()}>‹</button>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Service credits</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>View your available service credits</div>
        </div>
      </div>

      <ErrorBanner error={error} />

      {/* Balance card — real backend-computed SUM(remaining_amount), never summed client-side. */}
      <div className="co-card" style={{ marginBottom: 16, border: "1px solid var(--danger)" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <span aria-hidden="true" style={{ fontSize: 28, color: "var(--danger)" }}>👛</span>
          <div>
            <div style={{ fontWeight: 700 }}>Available service credit</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--danger)", margin: "4px 0" }}>
              {summary ? `${ccy}${Number(summary.active_credit_balance ?? 0).toLocaleString()}` : "—"}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Eligibility is confirmed when you book.
            </div>
          </div>
        </div>
      </div>

      {credits && credits.length > 2 && (
        <button className="co-btn-secondary"
          style={{ width: "100%", marginBottom: 16, color: "var(--danger)", borderColor: "var(--danger)" }}
          onClick={() => setShowAll((s) => !s)}>
          {showAll ? "Show less" : "View credit activity"}
        </button>
      )}

      <div style={{ fontWeight: 700, marginBottom: 8 }}>Recent activity</div>
      {credits === null ? (
        !error && <div className="co-skeleton" style={{ height: 120, marginBottom: 16 }} />
      ) : credits.length === 0 ? (
        <div className="co-card" style={{ textAlign: "center", padding: 24, color: "var(--text-tertiary)", marginBottom: 16 }}>
          You have no service credits yet. Credits from settlements or refunds appear here.
        </div>
      ) : (
        <div className="co-card" style={{ marginBottom: 16, padding: 0 }}>
          {visibleCredits!.map((c, i) => (
            <div key={c.id} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center", padding: 16,
              borderBottom: i < visibleCredits!.length - 1 ? "1px solid var(--border)" : "none",
            }}>
              <div>
                <div style={{ fontWeight: 700 }}>{SOURCE_LABEL[c.source] ?? c.source}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{fmtDate(c.created_at)}</div>
              </div>
              <div style={{ fontWeight: 700, color: "var(--danger)" }}>
                +{c.currency}{Number(c.amount).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontWeight: 700, marginBottom: 8 }}>Important to know</div>
      <div className="co-card" style={{ marginBottom: 16, padding: 0 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: 16, borderBottom: "1px solid var(--border)" }}>
          <span aria-hidden="true">🛡️</span>
          <div>
            <div style={{ fontWeight: 700 }}>Booking eligibility</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Credit use depends on the confirmed booking.</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: 16 }}>
          <span aria-hidden="true">👛</span>
          <div>
            <div style={{ fontWeight: 700 }}>Your balance</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Only completed credit transactions appear here.</div>
          </div>
        </div>
      </div>

      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <Link href="/customer/complaints" style={{ color: "var(--danger)", fontWeight: 600, textDecoration: "underline" }}>
          Get help with credits
        </Link>
      </div>

      <BottomNav />
    </div>
  );
}
