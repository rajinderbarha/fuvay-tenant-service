"use client";
/**
 * Public Tenant Registration — dynamic packages from backend.
 * Flow:
 *   1. Business Info + Vertical/Category selection
 *   2. Load active signup packages from /v1/public/packages?vertical_type=…
 *   3. Package selection
 *   4. OTP verify
 *   5. Payment via Razorpay
 *   6. Done — show credentials
 */

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Check, AlertTriangle, Sparkles, ArrowRight, ArrowLeft,
  PartyPopper, Info, ShieldCheck, FlaskConical, CreditCard,
  Loader2,
} from "lucide-react";
import { publicRegApi, publicPackagesApi, SignupPackage } from "../../lib/api";
import { Input, Btn } from "../../components/shared/ui";

type Step = "info" | "plans" | "otp" | "payment" | "done";

const STEP_LABELS = ["Business Info", "Choose Plan", "Verify OTP", "Payment", "Done"];

const VERTICALS = [
  { value: "home_services",         label: "Home Services"       },
  { value: "salon",                 label: "Salon & Beauty"      },
  { value: "coaching",              label: "Coaching / IELTS"    },
  { value: "real_estate",           label: "Real Estate"         },
  { value: "automotive",            label: "Automotive"          },
  { value: "cleaning_services",     label: "Cleaning Services"   },
  { value: "laundry",               label: "Laundry"             },
  { value: "restaurant",            label: "Restaurant"          },
  { value: "repair_services",       label: "Repair Services"     },
  { value: "professional_services", label: "Professional Services"},
  { value: "pharmacy",              label: "Pharmacy"            },
  { value: "hardware",              label: "Hardware"            },
  { value: "marketplace_products",  label: "Marketplace"         },
];

// Load Razorpay checkout.js lazily
function loadRazorpay(): Promise<boolean> {
  return new Promise(resolve => {
    if ((window as unknown as Record<string, unknown>).Razorpay) { resolve(true); return; }
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function RegisterPage() {
  const [step,    setStep]    = useState<Step>("info");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  const [form, setForm] = useState({
    business_name: "", owner_name: "", owner_email: "",
    owner_phone: "", city: "", country: "India", zipcode: "", state: "",
    vertical: "",
  });

  // Plans loaded from backend
  const [plans,        setPlans]        = useState<SignupPackage[]>([]);
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansError,   setPlansError]   = useState("");
  const [selectedPlan, setSelectedPlan] = useState<SignupPackage | null>(null);

  const [sessionId, setSessionId] = useState("");
  const [otp,       setOtp]       = useState("");
  const [devOtp,    setDevOtp]    = useState("");
  const [orderData, setOrderData] = useState<{order_id:string; amount:number; amount_inr:number; key_id:string; prefill:{name:string; email:string; contact:string}} | null>(null);
  const [result,    setResult]    = useState<{tenant_id:string; business_name:string; plan_type:string; trial_days:number; owner_email:string; temp_password:string} | null>(null);

  function setField(key: keyof typeof form) {
    return (v: string) => setForm(p => ({ ...p, [key]: v }));
  }

  // Load packages whenever vertical changes
  const loadPlans = useCallback(async (vertical: string) => {
    if (!vertical) { setPlans([]); return; }
    setPlansLoading(true);
    setPlansError("");
    try {
      const res = await publicPackagesApi.list(vertical);
      setPlans(res.packages ?? []);
      setSelectedPlan(null);
    } catch {
      setPlansError("Could not load packages. Please try again.");
      setPlans([]);
    } finally {
      setPlansLoading(false);
    }
  }, []);

  useEffect(() => {
    if (form.vertical) loadPlans(form.vertical);
  }, [form.vertical, loadPlans]);

  function handleInfoSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const required = ["business_name", "owner_name", "owner_email", "owner_phone", "city", "country", "zipcode", "vertical"] as const;
    for (const k of required) {
      if (!form[k].trim()) {
        setError(`${k.replace(/_/g, " ")} is required.`); return;
      }
    }
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(form.owner_email)) {
      setError("Please enter a valid email address."); return;
    }
    setStep("plans");
  }

  async function handleInitiate() {
    if (!selectedPlan) { setError("Please select a package."); return; }
    setError("");
    setLoading(true);
    try {
      const res = await publicRegApi.initiate(
        form.business_name, form.owner_name, form.owner_email,
        form.owner_phone, form.vertical, form.city,
        form.country, form.zipcode, form.state || undefined,
        selectedPlan.package_id,
      );
      if (res) {
        setSessionId(res.session_id);
        if (res.dev_otp) { setDevOtp(res.dev_otp); setOtp(res.dev_otp); } else { setDevOtp(""); }
        setStep("otp");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally { setLoading(false); }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    const trimmedOtp = otp.trim();
    if (!trimmedOtp || trimmedOtp.length < 4) { setError("Enter the OTP sent to your phone."); return; }
    setError(""); setLoading(true);
    try {
      const res = await publicRegApi.verify(sessionId, trimmedOtp);
      if (res?.verified) {
        const order = await publicRegApi.paymentOrder(sessionId);
        if (order) { setOrderData(order); setStep("payment"); }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed. Check your OTP and try again.");
    } finally { setLoading(false); }
  }

  async function handlePay() {
    if (!orderData) return;
    setError(""); setLoading(true);

    const loaded = await loadRazorpay();
    if (!loaded) {
      setError("Could not load payment gateway. Check your internet connection.");
      setLoading(false); return;
    }

    if (!orderData.key_id || orderData.order_id.startsWith("order_local_")) {
      try {
        const res = await publicRegApi.complete(sessionId, orderData.order_id, "pay_dev_bypass", "dev_sig", selectedPlan?.package_id);
        if (res) { setResult(res); setStep("done"); }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
      } finally { setLoading(false); }
      return;
    }

    const RazorpayClass = (window as unknown as { Razorpay: new (opts: Record<string, unknown>) => { open(): void } }).Razorpay;
    const rzp = new RazorpayClass({
      key: orderData.key_id, amount: orderData.amount, currency: "INR",
      name: "ServiceOS",
      description: selectedPlan?.name ?? "Plan",
      order_id: orderData.order_id, prefill: orderData.prefill,
      theme: { color: "#4F46E5" },
      handler: async (response: {razorpay_order_id:string; razorpay_payment_id:string; razorpay_signature:string}) => {
        try {
          const res = await publicRegApi.complete(sessionId, response.razorpay_order_id, response.razorpay_payment_id, response.razorpay_signature, selectedPlan?.package_id);
          if (res) { setResult(res); setStep("done"); }
        } catch (err: unknown) {
          setError(err instanceof Error ? err.message : "Payment successful but account creation failed. Please contact support.");
        } finally { setLoading(false); }
      },
      modal: { ondismiss: () => setLoading(false) },
    });
    rzp.open();
  }

  const stepNum = { info: 1, plans: 2, otp: 3, payment: 4, done: 5 }[step];

  // ── Format helpers
  function formatPrice(pkg: SignupPackage) {
    const sym = pkg.currency === "INR" ? "₹" : pkg.currency;
    const amount = pkg.package_price ?? pkg.price ?? 0;
    return `${sym}${amount.toLocaleString("en-IN")}`;
  }
  function formatCycle(pkg: SignupPackage) {
    if (!pkg.billing_cycle) return "";
    const map: Record<string,string> = { one_time: " one-time", monthly: "/mo", quarterly: "/qtr", yearly: "/yr" };
    return map[pkg.billing_cycle] ?? `/${pkg.billing_cycle}`;
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "48px 24px", display: "flex", flexDirection: "column", alignItems: "center" }}>

      {/* Logo */}
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ width: 56, height: 56, borderRadius: 14, background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px", boxShadow: "var(--shadow-md)" }}>
          <span style={{ color: "white", fontWeight: 800, fontSize: 22 }}>S</span>
        </div>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px", letterSpacing: "-0.02em" }}>ServiceOS</h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>Start your free trial in minutes</p>
      </div>

      {/* Step indicator */}
      {step !== "done" && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 28 }}>
          {STEP_LABELS.map((label, i) => (
            <React.Fragment key={label}>
              <div title={label} style={{
                width: 28, height: 28, borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 700, flexShrink: 0,
                border: `2px solid ${stepNum > i + 1 || stepNum === i + 1 ? "var(--brand)" : "var(--border)"}`,
                background: stepNum > i + 1 ? "var(--accent)" : stepNum === i + 1 ? "var(--brand)" : "transparent",
                color: stepNum >= i + 1 ? "#fff" : "var(--text-tertiary)",
                transition: "all 0.15s",
              }}>
                {stepNum > i + 1 ? <Check size={14}/> : i + 1}
              </div>
              {i < STEP_LABELS.length - 1 && (
                <div style={{ height: 2, width: 32, background: stepNum > i + 1 ? "var(--accent)" : "var(--border)", transition: "background 0.15s" }}/>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* ── Step 1: Business Info ── */}
      {step === "info" && (
        <form onSubmit={handleInfoSubmit} style={{ width: "100%", maxWidth: 860, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 18, padding: 36, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Tell us about your business</h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            Verify your phone, choose a plan, pay once, and your account is live instantly.
          </p>

          {error && <ErrorBanner text={error}/>}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
            <Input label="Business Name *" required placeholder="e.g. Rahul AC Services" value={form.business_name} onChange={setField("business_name")}/>
            <Input label="Your Full Name *" required placeholder="Owner's name" value={form.owner_name} onChange={setField("owner_name")}/>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
            <Input label="Email Address *" required type="email" placeholder="owner@business.com" value={form.owner_email} onChange={setField("owner_email")}/>
            <Input label="Phone Number *" required type="tel" placeholder="+91 9876543210" hint="OTP will be sent here" value={form.owner_phone} onChange={setField("owner_phone")}/>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 14 }}>
            <Input label="City *" required placeholder="e.g. Mumbai" value={form.city} onChange={setField("city")}/>
            <Input label="Country *" required placeholder="India" value={form.country} onChange={setField("country")}/>
            <Input label="Zipcode / PIN *" required placeholder="400001" value={form.zipcode} onChange={setField("zipcode")}/>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
            <Input label="State (optional)" placeholder="e.g. Maharashtra" value={form.state} onChange={setField("state")}/>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Business Vertical *</label>
              <select
                required
                value={form.vertical}
                onChange={e => setForm(p => ({ ...p, vertical: e.target.value }))}
                style={{
                  width: "100%", height: 40, padding: "0 12px", fontSize: 13, borderRadius: 8,
                  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                  outline: "none", fontFamily: "inherit",
                }}
              >
                <option value="">Select industry…</option>
                {VERTICALS.map(v => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>

          <Btn type="submit" variant="primary" size="lg" fullWidth>
            Continue to Plans <ArrowRight size={16}/>
          </Btn>
          <p style={{ textAlign: "center", marginTop: 16, fontSize: 13, color: "var(--text-secondary)" }}>
            Already registered? <Link href="/login" style={{ color: "var(--brand)", fontWeight: 600 }}>Sign in</Link>
          </p>
        </form>
      )}

      {/* ── Step 2: Plan Selection ── */}
      {step === "plans" && (
        <div style={{ width: "100%", maxWidth: 1000 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 18, padding: 36, boxShadow: "var(--shadow-lg)" }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Choose your plan
            </h2>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 22px" }}>
              Plans available for <strong style={{ color: "var(--brand)" }}>{VERTICALS.find(v => v.value === form.vertical)?.label ?? form.vertical}</strong>
            </p>

            {error && <ErrorBanner text={error}/>}
            {plansError && <ErrorBanner text={plansError}/>}

            {plansLoading && (
              <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-secondary)", display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
                <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }}/>
                <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
                Loading plans…
              </div>
            )}

            {!plansLoading && plans.length === 0 && !plansError && (
              <div style={{ textAlign: "center", padding: "40px 0" }}>
                <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 8 }}>
                  No signup plans are currently available for this vertical.
                </p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  Please contact us or try a different business category.
                </p>
              </div>
            )}

            {!plansLoading && plans.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(plans.length, 3)}, 1fr)`, gap: 16, marginBottom: 26 }}>
                {plans.map(pkg => {
                  const isSelected = selectedPlan?.package_id === pkg.package_id;
                  const pkgFeatures = (pkg.package_features ?? []).filter(f => f.is_included);
                  const pkgLimits   = pkg.package_limits ?? [];
                  const badgeText   = pkg.badge_label || (pkg.is_popular ? "Most Popular" : "");
                  return (
                    <div key={pkg.package_id} onClick={() => setSelectedPlan(pkg)} style={{
                      border: `2px solid ${isSelected ? "var(--brand)" : "var(--border)"}`,
                      background: isSelected ? "var(--accent-muted)" : "var(--surface)",
                      borderRadius: 14, padding: 20, cursor: "pointer", position: "relative",
                      transition: "all 0.15s",
                    }}>
                      {badgeText && (
                        <div style={{
                          position: "absolute", top: -11, left: "50%", transform: "translateX(-50%)",
                          background: "var(--golden)", color: "#1A1A18", fontSize: 11, fontWeight: 700,
                          padding: "3px 10px", borderRadius: 999, display: "flex", alignItems: "center", gap: 4,
                          whiteSpace: "nowrap", boxShadow: "var(--shadow-sm)",
                        }}>
                          <Sparkles size={11}/> {badgeText}
                        </div>
                      )}

                      <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>{pkg.name}</p>
                      <p style={{ fontSize: 22, fontWeight: 800, color: "var(--brand)", margin: "0 0 2px" }}>
                        {formatPrice(pkg)}<span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-tertiary)" }}>{formatCycle(pkg)}</span>
                      </p>
                      {pkg.validity_days && (
                        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>
                          Valid for {pkg.validity_days} days
                        </p>
                      )}

                      {/* Short/full description */}
                      {(pkg.short_description || pkg.description) && (
                        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 10px", lineHeight: 1.5 }}>
                          {pkg.short_description || pkg.description}
                        </p>
                      )}

                      {/* Security deposit note */}
                      {Number(pkg.security_deposit_amount) > 0 && (
                        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 8px",
                          padding: "4px 8px", background: "var(--warning-bg)", borderRadius: 5 }}>
                          + ₹{Number(pkg.security_deposit_amount).toLocaleString("en-IN")} security deposit
                        </p>
                      )}

                      {/* Included credits note */}
                      {Number(pkg.included_credit_amount) > 0 && (
                        <p style={{ fontSize: 11, color: "var(--success-text)", margin: "0 0 8px",
                          padding: "4px 8px", background: "var(--success-bg)", borderRadius: 5 }}>
                          Includes ₹{Number(pkg.included_credit_amount).toLocaleString("en-IN")} wallet credits
                        </p>
                      )}

                      {/* Features from backend */}
                      {pkgFeatures.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
                          {pkgFeatures.slice(0, 6).map(f => (
                            <div key={f.feature_id} style={{ display: "flex", alignItems: "flex-start", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                              <Check size={13}
                                color={f.is_highlighted ? "var(--brand)" : "var(--success)"}
                                style={{ flexShrink: 0, marginTop: 1 }}/>
                              <span style={{ fontWeight: f.is_highlighted ? 600 : 400, color: f.is_highlighted ? "var(--text-primary)" : undefined }}>
                                {f.feature_label}
                              </span>
                            </div>
                          ))}
                          {pkgFeatures.length > 6 && (
                            <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                              +{pkgFeatures.length - 6} more features
                            </p>
                          )}
                        </div>
                      )}

                      {/* Limits as chips */}
                      {pkgLimits.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 10 }}>
                          {pkgLimits.slice(0, 4).map(l => (
                            <span key={l.limit_id} style={{
                              fontSize: 10, padding: "2px 7px", borderRadius: 4,
                              background: "var(--surface-sunken)", color: "var(--text-tertiary)",
                              border: "1px solid var(--border)",
                            }}>
                              {l.is_unlimited ? "Unlimited" : l.limit_value} {l.limit_unit} {l.limit_label}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Terms summary */}
                      {pkg.terms_summary && (
                        <p style={{ fontSize: 10, color: "var(--text-tertiary)", margin: "10px 0 0", textAlign: "center" }}>
                          {pkg.terms_summary}
                        </p>
                      )}

                      {isSelected && (
                        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: "var(--brand)" }}>
                          <Check size={14}/> {pkg.cta_label || "Selected"}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            <div style={{ display: "flex", gap: 12 }}>
              <Btn variant="secondary" size="lg" icon={<ArrowLeft size={16}/>} onClick={() => { setStep("info"); setError(""); }}>
                Back
              </Btn>
              <Btn variant="primary" size="lg" style={{ flex: 1 }} loading={loading}
                disabled={!selectedPlan} onClick={handleInitiate}>
                {loading ? "Sending OTP…" : <>Continue <ArrowRight size={16}/></>}
              </Btn>
            </div>
          </div>
        </div>
      )}

      {/* ── Step 3: OTP Verification ── */}
      {step === "otp" && (
        <form onSubmit={handleVerify} style={{ width: "100%", maxWidth: 460, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 18, padding: 36, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Verify your phone</h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            We sent a 6-digit OTP to <strong style={{ color: "var(--text-primary)" }}>{form.owner_phone}</strong>.
          </p>

          {error && <ErrorBanner text={error}/>}

          <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 14px", borderRadius: 12, background: "var(--info-bg)", border: "1px solid var(--info-border)", marginBottom: 20, fontSize: 13, color: "var(--info-text)", lineHeight: 1.6 }}>
            <Info size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
            <span>Plan: <strong>{selectedPlan?.name}</strong> · {form.business_name} · {form.city}, {form.country}</span>
          </div>

          {devOtp && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: 10, background: "var(--golden-bg)", border: "1px solid var(--golden-border)", marginBottom: 18, fontSize: 13, color: "var(--golden-text)" }}>
              <FlaskConical size={14} style={{ flexShrink: 0 }}/>
              <span>Dev mode — OTP auto-filled: <strong>{devOtp}</strong></span>
            </div>
          )}

          <div style={{ marginBottom: 22 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 8 }}>Enter OTP</label>
            <input type="text" inputMode="numeric" maxLength={6} placeholder="——————" value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, ""))}
              style={{ width: "100%", height: 58, textAlign: "center", fontSize: 28, fontWeight: 700, letterSpacing: "0.5em", fontFamily: "inherit", color: "var(--text-primary)", background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 12, outline: "none", boxSizing: "border-box" }}
              onFocus={e => { e.currentTarget.style.borderColor = "var(--border-focus)"; }}
              onBlur={e  => { e.currentTarget.style.borderColor = "var(--border)"; }}/>
          </div>
          <Btn type="submit" variant="primary" size="lg" fullWidth loading={loading} disabled={otp.trim().length < 4}>
            {loading ? "Verifying…" : <>Verify Phone <ArrowRight size={16}/></>}
          </Btn>
          <Btn type="button" variant="ghost" size="md" fullWidth icon={<ArrowLeft size={14}/>} style={{ marginTop: 10 }}
            onClick={() => { setStep("plans"); setOtp(""); setDevOtp(""); setError(""); }}>
            Back / Resend OTP
          </Btn>
        </form>
      )}

      {/* ── Step 4: Payment ── */}
      {step === "payment" && orderData && (
        <div style={{ width: "100%", maxWidth: 460, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 18, padding: 36, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Complete Payment</h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            One payment activates your account. Your trial starts immediately after.
          </p>
          {error && <ErrorBanner text={error}/>}
          <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 12, padding: 18, marginBottom: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Plan</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{selectedPlan?.name}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Business</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{form.business_name}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <span style={{ fontSize: 15, fontWeight: 700 }}>Total</span>
              <span style={{ fontSize: 20, fontWeight: 800, color: "var(--brand)" }}>₹{orderData.amount_inr.toLocaleString("en-IN")}</span>
            </div>
          </div>
          {orderData.order_id.startsWith("order_local_") && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: 10, background: "var(--golden-bg)", border: "1px solid var(--golden-border)", marginBottom: 18, fontSize: 13, color: "var(--golden-text)" }}>
              <FlaskConical size={14} style={{ flexShrink: 0 }}/>
              <span>Dev mode — Razorpay not configured. Payment will be bypassed.</span>
            </div>
          )}
          <Btn variant="primary" size="lg" fullWidth loading={loading} icon={<CreditCard size={16}/>} onClick={handlePay}>
            {loading ? "Processing…" : `Pay ₹${orderData.amount_inr.toLocaleString("en-IN")} & Activate`}
          </Btn>
          <Btn variant="ghost" size="md" fullWidth icon={<ArrowLeft size={14}/>} style={{ marginTop: 10 }}
            onClick={() => { setStep("otp"); setError(""); }}>Back</Btn>
          <p style={{ textAlign: "center", fontSize: 11, color: "var(--text-tertiary)", marginTop: 16 }}>
            Secured by Razorpay · PCI DSS compliant
          </p>
        </div>
      )}

      {/* ── Step 5: Done ── */}
      {step === "done" && result && (
        <div style={{ width: "100%", maxWidth: 480, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 18, padding: 36, boxShadow: "var(--shadow-lg)", textAlign: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--success-bg)", border: "1px solid var(--success-border)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 18px", color: "var(--success-text)" }}>
            <PartyPopper size={28}/>
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            Welcome to ServiceOS!
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 6px", lineHeight: 1.6 }}>
            <strong style={{ color: "var(--text-primary)" }}>{result.business_name}</strong> is live on the{" "}
            <strong style={{ color: "var(--brand)" }}>{selectedPlan?.name ?? result.plan_type}</strong> plan.
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 24px" }}>
            Your <strong>{result.trial_days}-day free trial</strong> has started.
          </p>
          <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, fontSize: 13, color: "var(--text-secondary)", marginBottom: 22, textAlign: "left", lineHeight: 1.9 }}>
            <p style={{ margin: 0 }}><strong style={{ color: "var(--text-primary)" }}>Login Email:</strong> {result.owner_email}</p>
            <p style={{ margin: 0 }}><strong style={{ color: "var(--text-primary)" }}>Temp Password:</strong> <span style={{ fontFamily: "monospace" }}>{result.temp_password}</span></p>
            <p style={{ margin: "8px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>
              Save this now — it won&apos;t be shown again. You&apos;ll be prompted to set a new one on login.
            </p>
          </div>
          <Btn variant="primary" size="lg" fullWidth onClick={() => { window.location.href = "/login"; }}>
            Log In Now <ArrowRight size={16}/>
          </Btn>
        </div>
      )}

      <p style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-tertiary)", marginTop: 28 }}>
        <ShieldCheck size={13}/> Secured by ServiceOS Auth · JWT + TOTP
      </p>
    </div>
  );
}

function ErrorBanner({ text }: { text: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 18, lineHeight: 1.5 }}>
      <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
      <span>{text}</span>
    </div>
  );
}
