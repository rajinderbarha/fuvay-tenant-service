"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, PageShell } from "@serviceos/design-system";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { StepProgressBar } from "../../../../../../components/onboarding/StepProgressBar";
import { Card, Btn } from "../../../../../../components/shared/ui";
import { topupApi, inr, type TopupStatus, type TopupPlan } from "../../../../../../lib/api-topup";
import { activationPaymentApi } from "../../../../../../lib/api";
import { useRazorpayCheckout } from "../../../../../../hooks/useRazorpayCheckout";

export default function TechnicianPlanPage() {
  const [status, setStatus] = useState<TopupStatus | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const checkout = useRazorpayCheckout();
  const refresh = useCallback(async () => {
    try {
      setStatus(await topupApi.status());
      window.dispatchEvent(new Event("home-services-setup-updated"));
    }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load technician plans."); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function buy(plan: TopupPlan) {
    setBusy(true); setError(""); setNotice("");
    try {
      const order = await topupApi.createOrder(plan.id);
      if (!order.already_confirmed) {
        const payment = await checkout.open({ keyId: order.key, orderId: order.order_id,
          amountPaise: order.amount_paise, currency: order.currency, name: "Fuvay",
          description: `${plan.name} — ${plan.seats} technician seats` });
        await activationPaymentApi.confirmFunding(payment);
      }
      await refresh();
      setNotice("Payment confirmed. Your purchased technician seats are ready to use.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment could not be confirmed. Refresh before trying again; seats unlock only after server confirmation.");
    } finally { setBusy(false); }
  }

  return <OnboardingShell activeNav="plan"><PageShell>
    <PageHeader title="Choose your technician seat plan" description="Select a plan published by the administrator. Buy seats first, add your technicians next, then configure your team's working hours." />
    <StepProgressBar step={4} total={8} />
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <Card style={{ marginBottom: 20 }}>
      <h2>Only technicians use paid seats</h2>
      <p>Office staff and managers do not use technician seats. Buying a seat does not create booking capacity until a technician is added and ready.</p>
      <p>3 ready technicians × 4 two-hour windows in an 8-hour day = up to 12 jobs per day, with at most 3 jobs at the same time. You can set a lower daily limit.</p>
      <p>{status ? `${status.entitled_seats} purchased seats · ${status.used_seats} used · ${status.available_seats} available` : "Loading your seat entitlement…"}</p>
      <Btn variant="secondary" onClick={() => { setError(""); void refresh(); }}>Refresh payment & seats</Btn>
    </Card>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
      {status?.plans.map(plan => <Card key={plan.id}>
        <h2>{plan.name}{plan.is_default ? " · Recommended" : ""}</h2><p>{plan.description}</p>
        <p><strong>{plan.seats} technician seats</strong> · Staff members free</p>
        <p>{inr(plan.total_amount)} including {inr(plan.gst_amount)} GST</p>
        <p>Includes {inr(plan.credited_amount)} usage credit under this plan.</p>
        <p>Validity: {plan.validity_days ? `${plan.validity_days} days` : "No expiry"}</p>
        <Btn variant="primary" disabled={busy} onClick={() => void buy(plan)}>Buy this plan</Btn>
      </Card>)}
    </div>
    {status && status.plans.length === 0 && <p>No technician plan is published yet. Ask the administrator to publish a plan.</p>}
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
      <Link href="/tenant/home-services/setup/services-pricing">Back to services</Link>
      {status && status.entitled_seats > 0
        ? <Link href="/tenant/home-services/setup/staff">Continue to team setup</Link>
        : <p>Purchase a technician seat plan to unlock team setup. Office staff and managers do not consume seats.</p>}
    </div>
  </PageShell></OnboardingShell>;
}
