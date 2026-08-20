"use client";
/**
 * Tenant Onboarding — Finance Readiness (step 7 of 8).
 * Home Services: the customer pays the tenant's business directly.
 * ServiceOS never collects/holds/settles that payment — this step only
 * records HOW the tenant accepts it (direct payment methods) and the
 * tenant's invoice preferences.
 *
 * Security deposit + usage credit wallet: paid here via the same real
 * Razorpay flow the Activation Center uses (activationPaymentApi +
 * useRazorpayCheckout, backend: app.engines.vertical_catalog.
 * activation_payment_router — order creation + HMAC-verified webhook
 * confirmation, tenant.billing is only ever updated server-side). Product
 * decision (2026-08-04): pre-approval payment is allowed here, not just
 * post-approval on the Activation Center — required amounts are resolved
 * from the published finance policy regardless of enrollment status.
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Wallet, Banknote, Smartphone, CreditCard, Landmark, Info, ChevronRight,
  CheckCircle2, AlertTriangle, ShieldCheck, ClipboardList, TrendingUp,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { ProgressRing } from "../../../../../../components/onboarding/ProgressRing";
import { StepProgressBar } from "../../../../../../components/onboarding/StepProgressBar";
import { Card, Btn, Badge, Skeleton } from "../../../../../../components/shared/ui";
import {
  financeReadinessApi, activationPaymentApi, ServiceOSError,
  type FinanceReadinessManifest, type FinanceReadinessDirectPayment,
} from "../../../../../../lib/api";
import { useRazorpayCheckout } from "../../../../../../hooks/useRazorpayCheckout";

const METHODS: { key: keyof FinanceReadinessDirectPayment; label: string; icon: React.ReactNode; disabled?: boolean }[] = [
  { key: "accepts_cash", label: "Cash", icon: <Banknote size={20}/> },
  { key: "accepts_upi", label: "UPI", icon: <Smartphone size={20}/> },
  { key: "accepts_card_at_service_location", label: "Card at service location", icon: <CreditCard size={20}/>, disabled: true },
  { key: "accepts_bank_transfer", label: "Bank transfer", icon: <Landmark size={20}/> },
];

export default function FinanceReadinessPage() {
  const router = useRouter();
  const [manifest, setManifest] = useState<FinanceReadinessManifest | null>(null);
  const [form, setForm] = useState<FinanceReadinessDirectPayment | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);
  const [paymentNotice, setPaymentNotice] = useState<string | null>(null);
  const { open: openCheckout } = useRazorpayCheckout();

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    financeReadinessApi.get()
      .then(m => { setManifest(m); setForm(m.direct_payment); })
      .catch(e => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your finance readiness."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function payActivation() {
    setPaymentNotice(null);
    setPaying(true);
    let startedOrderId: string | null = null;
    try {
      const order = await activationPaymentApi.createFundingOrder();
      if (order.already_confirmed) {
        setPaymentNotice("Your earlier payment was found and confirmed. Balances have been refreshed.");
        load();
        return;
      }
      startedOrderId = order.order_id;

      // The signed order/payment tuple is verified by the backend. The
      // browser never supplies an amount or a deposit/credit allocation.
      const payment = await openCheckout({
        keyId: order.key, orderId: order.order_id, amountPaise: order.amount_paise,
        currency: order.currency, name: "Fuvay — Home Services Activation",
        description: order.quote?.checkout_mode === "credits_only"
          ? "Starter usage credits"
          : "Security deposit and starter credits",
      });
      await activationPaymentApi.confirmFunding(payment);
      setPaymentNotice("Payment confirmed. Your deposit and usage-credit balances have been updated.");
      load();
    } catch (e: unknown) {
      if (startedOrderId) {
        try {
          const reconciled = await activationPaymentApi.reconcileFunding(startedOrderId);
          if (reconciled.status === "captured" || reconciled.captured) {
            setPaymentNotice("Payment was captured and has now been reconciled successfully.");
            load();
            return;
          }
        } catch {
          // Preserve the original Checkout error below. The user can safely
          // retry; order creation also reconciles before reusing an order.
        }
      }
      setPaymentNotice(e instanceof ServiceOSError ? e.message
        : (e instanceof Error ? e.message : "Payment could not be started."));
    } finally {
      setPaying(false);
    }
  }

  async function save(andContinue: boolean) {
    if (!form) return;
    setSaving(true);
    setError("");
    try {
      const m = await financeReadinessApi.save(form);
      setManifest(m);
      setForm(m.direct_payment);
      if (andContinue) router.push("/tenant/home-services/setup/review");
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save finance readiness. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !manifest || !form) {
    return (
      <OnboardingShell activeNav="finance">
        <Skeleton height={60} style={{ marginBottom: 16 }}/>
        <Skeleton height={320} style={{ marginBottom: 16 }}/>
        <Skeleton height={200}/>
      </OnboardingShell>
    );
  }

  const actionsRemaining =
    (manifest.checks.direct_methods_selected ? 0 : 1) +
    (manifest.checks.invoice_details_complete ? 0 : 1);
  const funding = manifest.activation_requirements.funding_quote;
  const money = (value: number) => `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

  return (
    <OnboardingShell activeNav="finance">
      <style>{`
        .fin-grid { display: grid; grid-template-columns: minmax(0,1fr) 380px; gap: 28px; align-items: start; }
        .fin-methods { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .fin-policy-row { display: flex; justify-content: space-between; font-size: 12px; padding: 7px 0; border-bottom: 1px solid var(--border); }
        .fin-policy-row:last-child { border-bottom: none; }
        .fin-funding-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .fin-funding-account { display: flex; align-items: flex-start; gap: 10px; min-width: 0; padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-sunken); }
        .fin-funding-icon { width: 34px; height: 34px; display: grid; place-items: center; flex: 0 0 auto; color: var(--brand); border: 1px solid color-mix(in srgb, var(--brand) 32%, transparent); border-radius: 9px; background: color-mix(in srgb, var(--brand) 10%, transparent); }
        .fin-funding-label { margin: 0 0 3px; color: var(--text-secondary); font-size: 11.5px; font-weight: 650; }
        .fin-funding-value { margin: 0 0 4px; color: var(--text-primary); font-size: 18px; font-weight: 800; letter-spacing: -0.02em; }
        .fin-funding-value span { color: var(--text-tertiary); font-size: 10.5px; font-weight: 500; letter-spacing: 0; }
        .fin-funding-note { margin: 0; color: var(--text-tertiary); font-size: 10.5px; line-height: 1.45; }
        .fin-checkout-box { margin-top: 12px; padding: 15px; border: 1px solid color-mix(in srgb, var(--brand) 34%, var(--border)); border-radius: 12px; background: linear-gradient(145deg, color-mix(in srgb, var(--brand) 8%, var(--surface)), var(--surface)); }
        .fin-funding-line { display: flex; justify-content: space-between; gap: 16px; padding: 6px 0; color: var(--text-secondary); font-size: 12px; }
        .fin-funding-line strong { color: var(--text-primary); font-weight: 650; }
        .fin-funding-total { display: flex; justify-content: space-between; align-items: baseline; margin-top: 7px; padding-top: 11px; border-top: 1px solid var(--border); color: var(--text-primary); font-size: 13px; font-weight: 700; }
        .fin-funding-total strong { color: var(--brand); font-size: 22px; letter-spacing: -0.03em; }
        .fin-funded-banner { display: flex; gap: 10px; align-items: center; margin-top: 12px; padding: 13px 14px; color: var(--success); border: 1px solid color-mix(in srgb, var(--success) 35%, var(--border)); border-radius: 11px; background: color-mix(in srgb, var(--success) 8%, var(--surface)); }
        .fin-funded-banner div { display: flex; flex-direction: column; gap: 2px; }
        .fin-funded-banner strong { font-size: 12.5px; }
        .fin-funded-banner span { color: var(--text-secondary); font-size: 11px; }
        .fin-policy-unavailable { display: flex; gap: 8px; padding: 12px; color: var(--warning); border: 1px solid var(--warning-border, var(--border)); border-radius: 10px; background: var(--warning-bg, var(--surface-sunken)); font-size: 12px; }
        @media (max-width: 1000px) { .fin-grid { grid-template-columns: 1fr; } }
        @media (max-width: 640px) { .fin-methods { grid-template-columns: repeat(2, 1fr); } .fin-funding-grid { grid-template-columns: 1fr; } }
      `}</style>

      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Finance readiness</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Confirm how customer payments are recorded and review your Home Services finance policy.</p>
        </div>
        <Badge variant={actionsRemaining === 0 ? "success" : "warning"}>
          {actionsRemaining === 0 ? <CheckCircle2 size={12}/> : <AlertTriangle size={12}/>}
          {actionsRemaining === 0 ? "Ready for review" : `${actionsRemaining} action${actionsRemaining === 1 ? "" : "s"} remaining`}
        </Badge>
      </div>

      <StepProgressBar step={7} total={8} />

      <div className="fin-grid" style={{ marginTop: 20 }}>
        <div>
          <Card>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Customer payment collection</p>
            <div style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 18 }}>
              <Info size={15} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
              <span>{manifest.notice}</span>
            </div>

            <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Accepted direct payment methods</p>
            <div className="fin-methods" style={{ marginBottom: 20 }}>
              {METHODS.map(m => {
                const checked = !!form[m.key];
                return (
                  <button key={m.key as string} type="button" disabled={m.disabled}
                    onClick={() => !m.disabled && setForm({ ...form, [m.key]: !checked })}
                    style={{
                      display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
                      padding: "16px 10px", borderRadius: 10, cursor: m.disabled ? "not-allowed" : "pointer",
                      border: `1px solid ${checked ? "var(--brand)" : "var(--border)"}`,
                      background: checked ? "var(--brand-bg, rgba(232,124,42,0.08))" : "var(--surface)",
                      opacity: m.disabled ? 0.5 : 1, fontFamily: "inherit",
                    }}>
                    <span style={{ color: checked ? "var(--brand)" : "var(--text-tertiary)" }}>{m.icon}</span>
                    <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", textAlign: "center" }}>{m.label}</span>
                    <span style={{ fontSize: 10.5, fontWeight: 700, color: checked ? "var(--success)" : "var(--text-tertiary)" }}>
                      {m.disabled ? "Disabled" : (checked ? "Enabled" : "Off")}
                    </span>
                  </button>
                );
              })}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Payment confirmation required</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Staff records method, amount and reference after payment.</p>
              </div>
              <SwitchToggle label="Payment confirmation required" checked={form.payment_confirmation_required}
                onChange={v => setForm({ ...form, payment_confirmation_required: v })}/>
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Business invoice details</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 14 }}>
              <Field label="Invoice business name">
                <input aria-label="Invoice business name" value={form.invoice_business_name ?? manifest.invoice_defaults.business_name ?? ""}
                  onChange={e => setForm({ ...form, invoice_business_name: e.target.value })}
                  style={inputStyle}/>
              </Field>
              <Field label="GSTIN (optional)">
                <input aria-label="GSTIN" value={manifest.invoice_defaults.gstin ?? ""} disabled style={{ ...inputStyle, opacity: 0.7 }}/>
                {manifest.invoice_defaults.gstin_verified && (
                  <p style={{ fontSize: 11, color: "var(--success)", margin: "4px 0 0", display: "flex", alignItems: "center", gap: 4 }}>
                    <CheckCircle2 size={11}/> From verified profile
                  </p>
                )}
              </Field>
              <Field label="Invoice prefix">
                <input aria-label="Invoice prefix" value={form.invoice_prefix ?? ""} maxLength={20}
                  onChange={e => setForm({ ...form, invoice_prefix: e.target.value.toUpperCase() })}
                  placeholder="e.g. ACME" style={inputStyle}/>
              </Field>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Issue customer receipt</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Provider receipt for a direct payment — not a ServiceOS payment receipt.</p>
              </div>
              <SwitchToggle label="Issue customer receipt" checked={form.issue_customer_receipt}
                onChange={v => setForm({ ...form, issue_customer_receipt: v })}/>
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
              <div>
                <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Activation funding</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>One secure checkout, with deposit and usage credits recorded separately.</p>
              </div>
              {funding && <Badge variant={funding.can_pay ? "warning" : "success"}>{funding.can_pay ? "Payment required" : "Fully funded"}</Badge>}
            </div>
            {paymentNotice && (
              <div role="status" style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 12 }}>
                <Info size={14} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
                <span>{paymentNotice}</span>
              </div>
            )}
            {funding ? (
              <>
                <div className="fin-funding-grid">
                  <div className="fin-funding-account">
                    <div className="fin-funding-icon"><ShieldCheck size={18}/></div>
                    <div style={{ minWidth: 0 }}>
                      <p className="fin-funding-label">Security deposit</p>
                      <p className="fin-funding-value">{money(funding.deposit_held)} <span>held</span></p>
                      <p className="fin-funding-note">{funding.qualifying_technician_count} qualifying technician{funding.qualifying_technician_count === 1 ? "" : "s"} × {money(funding.deposit_per_technician)} = {money(funding.deposit_required)} required</p>
                    </div>
                    <CheckCircle2 size={17} style={{ color: funding.deposit_funded ? "var(--success)" : "var(--warning)", marginLeft: "auto" }}/>
                  </div>
                  <div className="fin-funding-account">
                    <div className="fin-funding-icon"><Wallet size={18}/></div>
                    <div style={{ minWidth: 0 }}>
                      <p className="fin-funding-label">Usage credit wallet</p>
                      <p className="fin-funding-value">{money(funding.starter_credit_balance)} <span>available</span></p>
                      <p className="fin-funding-note">Starter balance {money(funding.starter_credit_base)} · used for job-completion charges</p>
                    </div>
                    <CheckCircle2 size={17} style={{ color: funding.credits_funded ? "var(--success)" : "var(--warning)", marginLeft: "auto" }}/>
                  </div>
                </div>

                {funding.can_pay ? (
                  <div className="fin-checkout-box">
                    <div style={{ marginBottom: 12 }}>
                      <p style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 3px" }}>{funding.checkout_label}</p>
                      <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>Calculated live from your approved finance policy and qualifying team.</p>
                    </div>
                    {funding.deposit_shortfall > 0 && <FundingLine label={funding.deposit_held > 0 ? "Deposit top-up" : "Security deposit"} value={money(funding.deposit_shortfall)}/>} 
                    {funding.credit_purchase_base > 0 && <FundingLine label="Usage credits" value={money(funding.credit_purchase_base)}/>} 
                    {funding.credit_tax > 0 && <FundingLine label={`GST (${funding.credit_gst_percent}%)`} value={money(funding.credit_tax)}/>} 
                    <div className="fin-funding-total"><span>Payable now</span><strong>{money(funding.total_due)}</strong></div>
                    <Btn variant="primary" disabled={paying} onClick={payActivation} style={{ width: "100%", justifyContent: "center", marginTop: 12 }}>
                      {paying ? "Opening secure checkout…" : `${funding.checkout_label} · ${money(funding.total_due)}`}
                    </Btn>
                    <p style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 5, fontSize: 10.5, color: "var(--text-tertiary)", margin: "9px 0 0" }}>
                      <ShieldCheck size={12}/> Amounts are locked server-side and confirmed by the payment gateway.
                    </p>
                  </div>
                ) : (
                  <div className="fin-funded-banner"><CheckCircle2 size={18}/><div><strong>Activation funding complete</strong><span>Your deposit is fully held and starter credits are available.</span></div></div>
                )}
              </>
            ) : (
              <div role="alert" className="fin-policy-unavailable"><AlertTriangle size={16}/><span>The activation finance policy is not available yet. Contact support before making a payment.</span></div>
            )}
            <div style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", marginTop: 10 }}>
              <Info size={14} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
              <span>The security deposit is refundable subject to open jobs and claims. Usage credits are a separate spendable balance; they are never merged with the deposit.</span>
            </div>
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 16px" }}>Finance readiness</p>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
              <ProgressRing pct={manifest.readiness_percentage} tone={actionsRemaining === 0 ? "success" : "brand"} />
            </div>
            <CheckLine ok={manifest.checks.direct_methods_selected} label="Direct methods selected"/>
            <CheckLine ok={manifest.checks.confirmation_configured} label="Confirmation configured"/>
            <CheckLine ok={manifest.checks.invoice_details_complete} label="Invoice details complete"/>
            <CheckLine ok={!manifest.checks.activation_requirements_pending} pendingLabel="Activation requirements pending" label="Activation requirements clear"/>
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Home Services policy</p>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Revenue model</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.revenue_model}</span></div>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Customer pays</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.customer_pays}</span></div>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Job settlement</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.job_settlement}</span></div>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Pricing ownership</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.pricing_ownership}</span></div>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Provider commission</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.provider_commission_pct}%</span></div>
            <div className="fin-policy-row"><span style={{ color: "var(--text-tertiary)" }}>Policy version</span><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{manifest.policy.policy_version}</span></div>
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>What happens after activation</p>
            {[
              { icon: <ShieldCheck size={16}/>, text: "Your held security deposit automatically scales with the number of qualifying technicians." },
              { icon: <Wallet size={16}/>, text: "Usage credits stay separate and cover platform charges triggered by completed work." },
              { icon: <ClipboardList size={16}/>, text: "Commission is deducted only through the proven completion event, not at the time of booking." },
              { icon: <TrendingUp size={16}/>, text: "Direct payment records you confirm will be visible in Finance for transparency." },
            ].map((it, i) => (
              <div key={i} style={{ display: "flex", gap: 10, marginBottom: i === 3 ? 0 : 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--text-tertiary)" }}>{it.icon}</div>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{it.text}</p>
              </div>
            ))}
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Link href="/tenant/home-services/setup/staff"><Btn variant="secondary">Back</Btn></Link>
        <div style={{ display: "flex", gap: 10 }}>
          <Btn variant="secondary" disabled={saving} onClick={() => save(false)}>Save draft</Btn>
          <Btn variant="primary" disabled={saving} onClick={() => save(true)}>
            Save &amp; continue <ChevronRight size={15}/>
          </Btn>
        </div>
      </div>
    </OnboardingShell>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", height: 38, padding: "0 10px", fontSize: 13, borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
  boxSizing: "border-box", fontFamily: "inherit",
};

function SwitchToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-label={label} aria-checked={checked} onClick={() => onChange(!checked)}
      style={{
        width: 40, height: 22, borderRadius: 999, border: "none", cursor: "pointer", flexShrink: 0,
        background: checked ? "var(--brand)" : "var(--border)", position: "relative", transition: "background 0.15s",
      }}>
      <span style={{
        position: "absolute", top: 2, left: checked ? 20 : 2, width: 18, height: 18, borderRadius: "50%",
        background: "#fff", transition: "left 0.15s",
      }}/>
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  );
}

function CheckLine({ ok, label, pendingLabel }: { ok: boolean; label: string; pendingLabel?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
      {ok ? <CheckCircle2 size={14} style={{ color: "var(--success)" }}/> : <AlertTriangle size={14} style={{ color: "var(--warning)" }}/>}
      <span>{ok ? label : (pendingLabel ?? label)}</span>
    </div>
  );
}

function FundingLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="fin-funding-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
