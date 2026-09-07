"use client";
/**
 * Header credit pill + refill popup.
 *
 * Credit is the thing a provider can silently run out of: it is spent down by
 * commission on every completed job, and below the booking floor new bookings
 * stop arriving. Putting the number in the topbar means they see it falling
 * rather than discovering it from a rejected booking, and one click refills.
 *
 * The popup carries the plans that came back with the balance in the same
 * call, so opening it is instant — no spinner over a number just clicked.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Check, Users, Wallet, X, Zap } from "lucide-react";

import { topupApi, inr, type CreditState, type TopupPlan, type TopupStatus } from "../../lib/api-topup";
// Reuses the app's single Razorpay loader rather than declaring a second
// `window.Razorpay` global — two declarations of the same global disagree on
// its option type and break the build.
import { useRazorpayCheckout } from "../../hooks/useRazorpayCheckout";

/** Colour + wording per state. `blocked` and `arrears` are deliberately the
 *  same red: both mean bookings have stopped, which is the fact that matters. */
const TONE: Record<CreditState, { bg: string; border: string; fg: string; dot: string; label: string }> = {
  healthy: { bg: "var(--success-bg)", border: "var(--success-border)", fg: "var(--success-text)", dot: "var(--success)", label: "Credit" },
  low:     { bg: "var(--warning-bg)", border: "var(--warning-border)", fg: "var(--warning-text)", dot: "var(--warning)", label: "Credit low" },
  blocked: { bg: "var(--danger-bg)",  border: "var(--danger-border)",  fg: "var(--danger-text)",  dot: "var(--danger)",  label: "Bookings paused" },
  arrears: { bg: "var(--danger-bg)",  border: "var(--danger-border)",  fg: "var(--danger-text)",  dot: "var(--danger)",  label: "In arrears" },
};

export function CreditPill() {
  const razorpay = useRazorpayCheckout();
  const [status, setStatus] = useState<TopupStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await topupApi.status());
    } catch {
      // A provider on a non-Home-Services workspace has no credit wallet.
      // Render nothing rather than an error in the topbar of every page.
      setStatus(null);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  // Close on outside click / Escape — same behaviour as the notification bell
  // beside it, so the two popups feel like one control set.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function buy(plan: TopupPlan) {
    setBusy(true); setErr(null); setDone(null);
    try {
      const order = await topupApi.createOrder(plan.id);
      await razorpay.open({
        keyId: order.key,
        orderId: order.order_id,
        amountPaise: order.amount_paise,
        currency: order.currency,
        name: "Fuvay",
        description: `${plan.name} — ${inr(plan.credited_amount)} credit + ${plan.seats} seat(s)`,
      });
      // Seats and credit are granted by the captured-payment webhook, never by
      // this handler: a closed browser must not cost a provider what they paid.
      // This only re-reads what is already true server-side.
      setDone("Payment received — credit and seats will appear momentarily.");
      setTimeout(() => { void refresh(); }, 2500);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Dismissing the popup is a choice, not a failure worth shouting about.
      if (!/dismiss|cancel/i.test(msg)) setErr(msg);
    } finally {
      setBusy(false);
    }
  }

  if (!status) return null;

  const tone = TONE[status.state];
  const pct = status.warning_threshold > 0
    ? Math.max(0, Math.min(100, (status.credit_balance / status.warning_threshold) * 100))
    : 100;

  return (
    <div ref={wrapRef} className="provider-credit-pill" style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(o => !o)}
        aria-label={`Credit balance ${inr(status.credit_balance)}. Click to top up.`}
        aria-expanded={open}
        title={`${tone.label}: ${inr(status.credit_balance)} — click to top up`}
        style={{
          display: "flex", alignItems: "center", gap: 7, height: 38, padding: "0 12px",
          borderRadius: 999, background: tone.bg, border: `1px solid ${tone.border}`,
          cursor: "pointer", fontFamily: "inherit",
        }}
      >
        <Wallet size={14} style={{ color: tone.fg }} />
        <span style={{ fontSize: 13, fontWeight: 700, color: tone.fg }}>
          {inr(status.credit_balance)}
        </span>
        {status.state !== "healthy" && (
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: tone.dot }} />
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Top up credit"
          style={{
            position: "absolute", top: 44, right: 0, width: 380, maxHeight: "78vh",
            overflowY: "auto", background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-lg)", zIndex: 200,
          }}
        >
          {/* ── Balance ─────────────────────────────────────────────────── */}
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                Usage credit
              </span>
              <button onClick={() => setOpen(false)} aria-label="Close"
                      style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
                <X size={15} />
              </button>
            </div>

            <div style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "6px 0 2px" }}>
              {inr(status.credit_balance)}
            </div>

            {/* Distance to the floor, not an abstract percentage. */}
            <div style={{ height: 5, borderRadius: 3, background: "var(--surface-sunken)", overflow: "hidden", margin: "8px 0 6px" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: tone.dot, transition: "width .3s" }} />
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", lineHeight: 1.55 }}>
              Bookings pause below {inr(status.booking_floor)}. We warn you at {inr(status.warning_threshold)}.
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <Chip icon={<Users size={11} />}
                    label={`${status.used_seats}/${status.entitled_seats} seats used`} />
              <Chip icon={<Zap size={11} />}
                    label={`${status.entitled_seats} job${status.entitled_seats === 1 ? "" : "s"} per slot`} />
            </div>
          </div>

          {/* ── State banner ────────────────────────────────────────────── */}
          {status.state !== "healthy" && (
            <div style={{
              display: "flex", gap: 9, alignItems: "flex-start", padding: "11px 16px",
              background: tone.bg, borderBottom: "1px solid var(--border)",
              fontSize: 12, color: tone.fg, lineHeight: 1.55,
            }}>
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                {status.state === "arrears" &&
                  "Your balance is negative. New bookings are paused until it is cleared."}
                {status.state === "blocked" &&
                  "Below the booking floor — you are not receiving new bookings. Top up to resume."}
                {status.state === "low" &&
                  "Running low. Top up before you reach the floor and bookings pause."}
              </span>
            </div>
          )}
          {status.seats_over_limit && (
            <div style={{
              display: "flex", gap: 9, alignItems: "flex-start", padding: "11px 16px",
              background: "var(--warning-bg)", borderBottom: "1px solid var(--border)",
              fontSize: 12, color: "var(--warning-text)", lineHeight: 1.55,
            }}>
              <Users size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                You have {status.used_seats} technicians but only {status.entitled_seats} seats.
                Buy a plan to cover them.
              </span>
            </div>
          )}

          {err && (
            <div style={{ padding: "10px 16px", fontSize: 12, color: "var(--danger-text)", background: "var(--danger-bg)" }}>
              {err}
            </div>
          )}
          {done && (
            <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "10px 16px", fontSize: 12, color: "var(--success-text)", background: "var(--success-bg)" }}>
              <Check size={14} /> {done}
            </div>
          )}

          {/* ── Plans ───────────────────────────────────────────────────── */}
          <div style={{ padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--text-tertiary)", padding: "2px 4px 8px" }}>
              Top up
            </div>

            {status.plans.length === 0 && (
              <div style={{ padding: "18px 6px", fontSize: 12.5, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
                No top-up plans are available right now. Contact support if you need to add credit.
              </div>
            )}

            <div style={{ display: "grid", gap: 8 }}>
              {status.plans.map(p => (
                <button
                  key={p.id}
                  onClick={() => buy(p)}
                  disabled={busy}
                  style={{
                    textAlign: "left", padding: "11px 13px", borderRadius: "var(--radius-lg)",
                    border: `1px solid ${p.is_default ? "var(--brand)" : "var(--border)"}`,
                    background: "var(--surface)", cursor: busy ? "wait" : "pointer",
                    fontFamily: "inherit", opacity: busy ? 0.6 : 1,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>{p.name}</span>
                    <span style={{ marginLeft: "auto", fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>
                      {inr(p.total_amount)}
                    </span>
                  </div>
                  {/* The split, stated plainly: GST is not credit. */}
                  <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.6 }}>
                    {inr(p.credited_amount)} credit + {p.seats} technician seat{p.seats === 1 ? "" : "s"}
                    <br />
                    <span style={{ color: "var(--text-tertiary)" }}>
                      incl. {inr(p.gst_amount)} GST ({p.gst_percent}%) — GST is not added to credit
                    </span>
                  </div>
                </button>
              ))}
            </div>

            <a href="/home-services/finance?tab=topups"
               style={{ display: "block", textAlign: "center", marginTop: 10, fontSize: 12, color: "var(--brand)", textDecoration: "none" }}>
              View credit history →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 8px",
      borderRadius: 999, background: "var(--surface-sunken)", border: "1px solid var(--border)",
      fontSize: 11, color: "var(--text-secondary)",
    }}>
      {icon} {label}
    </span>
  );
}
