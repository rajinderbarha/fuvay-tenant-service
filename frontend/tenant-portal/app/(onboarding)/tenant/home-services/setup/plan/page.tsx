"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Check, CircleMinus, Clock3, IndianRupee, RefreshCw } from "lucide-react";
import { PageShell } from "@serviceos/design-system";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { Btn } from "../../../../../../components/shared/ui";
import { topupApi, completeTopupPayment, inr, type TopupStatus, type TopupPlan } from "../../../../../../lib/api-topup";
import { useRazorpayCheckout } from "../../../../../../hooks/useRazorpayCheckout";
import styles from "./plan.module.css";

export default function TechnicianPlanPage() {
  const [status, setStatus] = useState<TopupStatus | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const checkout = useRazorpayCheckout();

  const refresh = useCallback(async () => {
    try {
      setError("");
      setStatus(await topupApi.status());
      window.dispatchEvent(new Event("home-services-setup-updated"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load technician plans.");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function buy(plan: TopupPlan) {
    setBusyPlanId(plan.id);
    setError("");
    setNotice("");
    try {
      const order = await topupApi.createOrder(plan.id);
      await completeTopupPayment(order, () => checkout.open({
          keyId: order.key,
          orderId: order.order_id,
          amountPaise: order.amount_paise,
          currency: order.currency,
          name: "Fuvay",
          description: `${plan.name} — ${plan.seats} technician seats`,
      }));
      await refresh();
      window.dispatchEvent(new Event("home-services-credit-updated"));
      setNotice("Payment confirmed. Your technician seats and usage credit are ready.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment could not be confirmed. Refresh before trying again; seats unlock only after server confirmation.");
    } finally {
      setBusyPlanId(null);
    }
  }

  return (
    <OnboardingShell activeNav="plan">
      <PageShell>
        <div className={styles.page}>
          {status && !status.checkout_configured && (
            <div className={styles.gatewayWarning} role="alert">
              <span className={styles.warningIcon}><AlertTriangle size={16}/></span>
              <span>Payment checkout is not configured on this server. An administrator must save, test, and enable the Razorpay test Key ID and Key Secret.</span>
            </div>
          )}

          {error && <div className={styles.error} role="alert"><AlertTriangle size={16}/><span>{error}</span></div>}
          {notice && <div className={styles.notice} role="status"><Check size={16}/><span>{notice}</span></div>}

          <section className={styles.seatStrip} aria-label="Technician seat usage">
            <div className={styles.stripCopy}>
              <span className={styles.stripIcon}><CircleMinus size={15}/></span>
              <p>Only technicians use paid seats — staff and managers are free, and a seat adds capacity once a technician is added and ready.</p>
            </div>
            <div className={styles.seatActions}>
              <dl className={styles.seatStats}>
                <div><dt>purchased</dt><dd>{status?.entitled_seats ?? 0}</dd></div>
                <div><dt>used</dt><dd>{status?.used_seats ?? 0}</dd></div>
                <div><dt>available</dt><dd>{status?.available_seats ?? 0}</dd></div>
              </dl>
              <Btn variant="secondary" size="sm" onClick={() => void refresh()}>
                <RefreshCw size={13}/> Refresh
              </Btn>
            </div>
          </section>

          <div className={styles.sectionHeading}>
            <h1>Available plans</h1>
            <p>Published by the administrator. Pick the one that fits your team size.</p>
          </div>

          <div className={styles.planGrid}>
            {status?.plans.map(plan => (
              <article key={plan.id} className={`${styles.planCard} ${plan.is_default ? styles.recommended : ""}`}>
                {plan.is_default && <span className={styles.recommendedBadge}>Recommended</span>}
                <header className={styles.planHeader}>
                  <h2>{plan.name} — {plan.seats} seat{plan.seats === 1 ? "" : "s"}</h2>
                  <p>{plan.description || `${inr(plan.credited_amount)} usable credit and ${plan.seats} technician seat${plan.seats === 1 ? "" : "s"}.`}</p>
                </header>

                <div className={styles.priceLine}>
                  <strong>{inr(plan.total_amount)}</strong>
                  <span>incl. {inr(plan.gst_amount)} GST</span>
                </div>

                <div className={styles.features}>
                  <PlanFeature icon={<CircleMinus size={13}/>} value={`${plan.seats} seat${plan.seats === 1 ? "" : "s"}`} label="Technician seats" emphasized={plan.is_default}/>
                  <PlanFeature icon={<Check size={14}/>} value="Free" label="Staff members"/>
                  <PlanFeature icon={<IndianRupee size={14}/>} value={inr(plan.credited_amount)} label="Usage credit included"/>
                  <PlanFeature icon={<Clock3 size={14}/>} value={plan.validity_days ? `${plan.validity_days} days` : "No expiry"} label="Plan validity"/>
                </div>

                <button
                  type="button"
                  className={`${styles.buyButton} ${plan.is_default ? styles.primaryBuy : ""}`}
                  disabled={busyPlanId !== null || status.checkout_configured === false}
                  onClick={() => void buy(plan)}
                >
                  {busyPlanId === plan.id ? "Opening secure checkout…" : "Buy this plan"}
                </button>
              </article>
            ))}
          </div>

          {!status && !error && <p className={styles.empty}>Loading technician plans…</p>}
          {status && status.plans.length === 0 && <p className={styles.empty}>No technician plan is published yet. Ask the administrator to publish a plan.</p>}

          <footer className={styles.footer}>
            <Link href="/tenant/home-services/setup/services-pricing">← Back to services</Link>
            {status && status.entitled_seats > 0
              ? <Link href="/tenant/home-services/setup/staff">Continue to team setup →</Link>
              : <p>Purchase a technician seat plan to unlock team setup. Office staff and managers do not consume seats.</p>}
          </footer>
        </div>
      </PageShell>
    </OnboardingShell>
  );
}

function PlanFeature({ icon, value, label, emphasized = false }: {
  icon: React.ReactNode; value: string; label: string; emphasized?: boolean;
}) {
  return <div className={`${styles.feature} ${emphasized ? styles.featureEmphasis : ""}`}>
    <span className={styles.featureIcon}>{icon}</span>
    <span><strong>{value}</strong><small>{label}</small></span>
  </div>;
}
