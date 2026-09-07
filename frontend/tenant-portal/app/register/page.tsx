"use client";
/**
 * Tenant Signup — 5-step no-payment wizard, wired to the real backend.
 *
 * Layout matches the approved external design (left step rail + right
 * form card) — supplied as reference images. Rebuilt directly against
 * those references.
 *
 * REAL BACKEND (corrected): this wizard now calls
 * `/v1/public/signup/*` (`RegistrationService` via
 * app/engines/public_registration/signup_router.py). That service was
 * fully built already -- real OTP, password hashing, atomic
 * tenant+user+enrollment creation, auto-login -- but was never mounted, so
 * an earlier version of this page posted to the WRONG backend
 * (`publicTenantSignupApi`, an admin-lead-queue flow with no login until
 * manual approval). That mismatch is why a completed signup had no way to
 * log in or reach the setup wizard. The intended flow is: signup (no
 * payment) -> auto-login -> complete vertical setup -> submit for admin
 * review -> activation. See lib/api.ts `publicSignupApi`.
 */
import React, { useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import Script from "next/script";
import {
  Building2, CheckCircle2, Clock, Eye, EyeOff, Lock, Mail,
  Phone, ShieldCheck, User, ArrowRight, ArrowLeft, FileText, RefreshCw,
  Wrench, Scissors, GraduationCap, Car, Sparkles, Shirt, Utensils,
  Briefcase, Pill, Hammer, Store,
} from "lucide-react";
import { Button, Alert, Card } from "@serviceos/design-system";
import { publicSignupApi, SignupVertical } from "../../lib/api";
import styles from "./register.module.css";

const VERTICAL_ICONS: Record<string, React.ElementType> = {
  home_services: Wrench, real_estate: Building2, salon: Scissors, coaching: GraduationCap,
  automotive: Car, cleaning_services: Sparkles, laundry: Shirt, restaurant: Utensils,
  repair_services: Hammer, professional_services: Briefcase, pharmacy: Pill, hardware: Store,
};

type StepId = "account" | "verify" | "identity" | "vertical" | "review";
const SIGNUP_DRAFT_KEY = "serviceos_provider_signup_draft";
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";
const STEPS: { id: StepId; label: string; desc: string }[] = [
  { id: "account",  label: "Owner Account",   desc: "Secure your login" },
  { id: "verify",   label: "Verify Contact",  desc: "Mobile and email verification" },
  { id: "identity", label: "Business Identity", desc: "Legal business information" },
  { id: "vertical", label: "Select Vertical",  desc: "Choose where to start" },
  { id: "review",   label: "Review & Consent", desc: "Confirm and create workspace" },
];

function passwordScore(pw: string): number {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/[0-9]/.test(pw) || /[^A-Za-z0-9]/.test(pw)) s++;
  if (pw.length >= 12) s++;
  return s;
}

function Field({
  label, icon, type = "text", value, onChange, placeholder, required, trailing, autoComplete,
}: {
  label: string; icon?: React.ReactNode; type?: string; value: string;
  onChange: (v: string) => void; placeholder?: string; required?: boolean;
  trailing?: React.ReactNode; autoComplete?: string;
}) {
  const [focused, setFocused] = useState(false);
  const id = React.useId();
  return (
    <div>
      <label htmlFor={id} style={{ display: "block", fontSize: 12, lineHeight: 1, fontWeight: 600, color: "var(--text-primary)", marginBottom: 7 }}>
        {label}{required && <span style={{ color: "var(--danger-text)" }}> *</span>}
      </label>
      {/* Bordered icon cell, matching the field style used on /login. */}
      <div style={{
        position: "relative", display: "flex", alignItems: "center", height: 46, gap: 10, padding: "0 13px",
        background: "var(--surface-sunken)", border: `1.5px solid ${focused ? "var(--border-focus)" : "var(--border-strong)"}`,
        borderRadius: 12, transition: "border-color 0.15s ease, box-shadow 0.15s ease",
        boxShadow: focused ? "0 0 0 3px rgba(15,107,96,.08)" : "none",
      }}>
        {icon && (
          <span style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "var(--text-tertiary)", flexShrink: 0,
          }}>
            {icon}
          </span>
        )}
        <input
          id={id}
          type={type} value={value} required={required} autoComplete={autoComplete}
          onChange={e => onChange(e.target.value)} placeholder={placeholder}
          onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
          style={{
            flex: 1, height: "100%", padding: `0 ${trailing ? 28 : 0}px 0 0`,
            fontSize: 14, background: "transparent", border: "none",
            color: "var(--text-primary)", outline: "none",
            fontFamily: "inherit", boxSizing: "border-box", minWidth: 0,
          }}
        />
        {trailing && <span style={{ position: "absolute", right: 14, display: "flex" }}>{trailing}</span>}
      </div>
    </div>
  );
}

function PasswordField({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <Field
      label={label} icon={<Lock size={16} />} type={show ? "text" : "password"}
      value={value} onChange={onChange} placeholder={placeholder} required autoComplete="new-password"
      trailing={
        <button type="button" onClick={() => setShow(s => !s)} aria-label={show ? "Hide password" : "Show password"}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      }
    />
  );
}

export default function RegisterPage() {
  const [stepIndex, setStepIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [draftLoaded, setDraftLoaded] = useState(false);

  const [registrationId, setRegistrationId] = useState<string | null>(null);
  const [devOtps, setDevOtps] = useState<Record<string, string> | null>(null);
  const [mobileVerified, setMobileVerified] = useState(false);
  const [emailVerified, setEmailVerified] = useState(false);
  const [mobileOtp, setMobileOtp] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [otpBusy, setOtpBusy] = useState<"mobile" | "email" | null>(null);
  const [otpNotice, setOtpNotice] = useState<Partial<Record<"mobile" | "email", string>>>({});
  const [verticals, setVerticals] = useState<SignupVertical[]>([]);
  const [verticalsLoaded, setVerticalsLoaded] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState("");
  const turnstileContainerRef = useRef<HTMLDivElement>(null);
  const turnstileWidgetRef = useRef<string | null>(null);

  const renderTurnstile = useCallback(() => {
    if (!TURNSTILE_SITE_KEY || !turnstileContainerRef.current || turnstileWidgetRef.current) return;
    const api = (window as typeof window & { turnstile?: {
      render: (element: HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId: string) => void;
    } }).turnstile;
    if (!api) return;
    turnstileWidgetRef.current = api.render(turnstileContainerRef.current, {
      sitekey: TURNSTILE_SITE_KEY,
      action: "provider_signup",
      callback: (token: string) => { setTurnstileToken(token); setError(""); },
      "expired-callback": () => setTurnstileToken(""),
      "error-callback": () => setTurnstileToken(""),
    });
  }, []);

  function resetTurnstile() {
    setTurnstileToken("");
    const api = (window as typeof window & { turnstile?: { reset: (widgetId: string) => void } }).turnstile;
    if (api && turnstileWidgetRef.current) api.reset(turnstileWidgetRef.current);
  }

  const [form, setForm] = useState({
    owner_name: "", owner_email: "", owner_phone: "",
    password: "", confirmPassword: "",
    business_name: "", gstin: "", description: "",
    city: "", state: "",
    vertical: "",
    authorized: false, agreedTerms: false, marketingOptIn: false,
  });
  const set = useCallback(<K extends keyof typeof form>(k: K, v: (typeof form)[K]) => {
    setError("");
    setForm(f => ({ ...f, [k]: v }));
  }, []);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(SIGNUP_DRAFT_KEY) || "null");
      if (saved?.registrationId) {
        setRegistrationId(saved.registrationId);
        setStepIndex(Math.min(Math.max(Number(saved.stepIndex) || 0, 0), STEPS.length - 1));
        setMobileVerified(Boolean(saved.mobileVerified));
        setEmailVerified(Boolean(saved.emailVerified));
        if (saved.form) {
          setForm(current => ({ ...current, ...saved.form, password: "", confirmPassword: "" }));
        }
      }
    } catch {
      localStorage.removeItem(SIGNUP_DRAFT_KEY);
    } finally {
      setDraftLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!draftLoaded || !registrationId) return;
    const safeForm = { ...form, password: "", confirmPassword: "" };
    localStorage.setItem(SIGNUP_DRAFT_KEY, JSON.stringify({
      registrationId, stepIndex, mobileVerified, emailVerified, form: safeForm,
    }));
  }, [draftLoaded, registrationId, stepIndex, mobileVerified, emailVerified, form]);

  const step = STEPS[stepIndex];
  const pct = Math.round(((stepIndex + 1) / STEPS.length) * 100);
  const pwScore = passwordScore(form.password);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY || step.id !== "account") return;

    // The account step unmounts while the user moves through the wizard. If
    // they navigate back, the old widget id points at a detached element and
    // must not prevent a fresh challenge from rendering in the new container.
    turnstileWidgetRef.current = null;
    const timer = window.setTimeout(renderTurnstile, 0);
    return () => {
      window.clearTimeout(timer);
      const api = (window as typeof window & { turnstile?: {
        remove?: (widgetId: string) => void;
      } }).turnstile;
      if (turnstileWidgetRef.current) {
        api?.remove?.(turnstileWidgetRef.current);
        turnstileWidgetRef.current = null;
      }
      setTurnstileToken("");
    };
  }, [step.id, renderTurnstile]);

  useEffect(() => {
    if (step.id !== "vertical" || verticalsLoaded) return;
    publicSignupApi.listVerticals()
      .then(res => { setVerticals(res.verticals); setVerticalsLoaded(true); })
      .catch(() => setVerticalsLoaded(true));
  }, [step.id, verticalsLoaded]);

  function stepValid(id: StepId): boolean {
    switch (id) {
      case "account":
        return !!(form.owner_name && form.owner_phone && form.owner_email &&
          form.password && form.password === form.confirmPassword && pwScore >= 2);
      case "verify":
        return mobileVerified && emailVerified;
      case "identity":
        return !!(form.business_name && form.city && form.state);
      case "vertical":
        return !!form.vertical;
      case "review":
        return form.authorized && form.agreedTerms;
      default:
        return false;
    }
  }

  async function goNext() {
    if (step.id === "account") {
      if (!stepValid("account")) { setError("Please complete the required fields before continuing."); return; }
      if (TURNSTILE_SITE_KEY && !turnstileToken) { setError("Please complete the security check."); return; }
      setSubmitting(true); setError("");
      try {
        const res = await publicSignupApi.ownerAccount({
          full_name: form.owner_name, email: form.owner_email, mobile: form.owner_phone,
          password: form.password, password_confirm: form.confirmPassword,
          registration_id: registrationId ?? undefined,
          turnstile_token: turnstileToken || undefined,
        });
        if (res.existing_account || !res.registration_id) {
          setError(res.message || "An account already exists. Sign in or recover your account.");
          return;
        }
        setRegistrationId(res.registration_id);
        setMobileVerified(!!res.mobile_verified);
        setEmailVerified(!!res.email_verified);
        const compatibleDevOtps = res.dev_otps ?? {
          ...(res.dev_otp_mobile ? { mobile: res.dev_otp_mobile } : {}),
          ...(res.dev_otp_email ? { email: res.dev_otp_email } : {}),
        };
        setDevOtps(Object.keys(compatibleDevOtps).length ? compatibleDevOtps : null);
        setError("");
        setStepIndex(i => i + 1);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't create your account. Please try again.");
      } finally {
        resetTurnstile();
        setSubmitting(false);
      }
      return;
    }
    if (step.id === "identity") {
      if (!stepValid("identity") || !registrationId) { setError("Please complete the required fields before continuing."); return; }
      setSubmitting(true); setError("");
      try {
        await publicSignupApi.businessIdentity({
          registration_id: registrationId, business_name: form.business_name,
          gstin: form.gstin || undefined, description: form.description || undefined,
          registered_address: { city: form.city, state: form.state },
        });
        setStepIndex(i => i + 1);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't save business details. Please try again.");
      } finally {
        setSubmitting(false);
      }
      return;
    }
    if (step.id === "vertical") {
      if (!stepValid("vertical") || !registrationId) { setError("Please select a vertical to continue."); return; }
      setSubmitting(true); setError("");
      try {
        await publicSignupApi.selectVertical(registrationId, form.vertical);
        setStepIndex(i => i + 1);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't save your vertical selection. Please try again.");
      } finally {
        setSubmitting(false);
      }
      return;
    }
    if (!stepValid(step.id)) { setError("Please complete the required fields before continuing."); return; }
    setError("");
    setStepIndex(i => Math.min(i + 1, STEPS.length - 1));
  }
  function goBack() {
    setError("");
    setStepIndex(i => Math.max(i - 1, 0));
  }

  async function verifyChannel(channel: "mobile" | "email") {
    if (!registrationId) return;
    const otp = channel === "mobile" ? mobileOtp : emailOtp;
    if (!otp) { setError(`Enter the ${channel} code first.`); return; }
    setOtpBusy(channel); setError("");
    try {
      const res = await publicSignupApi.verifyContact(registrationId, channel, otp);
      setMobileVerified(res.mobile_verified);
      setEmailVerified(res.email_verified);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Couldn't verify that ${channel} code.`);
    } finally {
      setOtpBusy(null);
    }
  }

  async function resendOtp(channel: "mobile" | "email") {
    if (!registrationId) return;
    setOtpBusy(channel); setError("");
    setOtpNotice(current => ({ ...current, [channel]: undefined }));
    try {
      const res = await publicSignupApi.resendOtp(registrationId, channel);
      if (res.dev_otp) {
        setDevOtps(current => ({ ...(current ?? {}), [channel]: res.dev_otp as string }));
      }
      setOtpNotice(current => ({ ...current, [channel]: `A new ${channel} code was sent.` }));
    } catch (e) {
      setError(e instanceof Error ? e.message : `Couldn't resend the ${channel} code.`);
    } finally {
      setOtpBusy(null);
    }
  }

  async function submit() {
    if (!stepValid("review") || !registrationId) { setError("Please confirm both required checkboxes."); return; }
    setSubmitting(true); setError("");
    try {
      // Stable across retries and reloads after a lost completion response.
      const idempotencyKey = `signup-complete:${registrationId}`;
      const res = await publicSignupApi.complete(
        registrationId, idempotencyKey, form.authorized, form.agreedTerms, form.marketingOptIn,
      );
      localStorage.setItem("serviceos_tenant_token", res.access_token);
      if (res.refresh_token) localStorage.setItem("serviceos_tenant_refresh", res.refresh_token);
      localStorage.setItem("serviceos_tenant_id", res.tenant_id);
      localStorage.setItem("serviceos_tenant_vertical", res.vertical_key);
      localStorage.removeItem(SIGNUP_DRAFT_KEY);
      // Only the home_services vertical has a built setup wizard today; any
      // other vertical lands on the dashboard rather than a fabricated wizard.
      window.location.href = res.vertical_key === "home_services"
        ? "/tenant/home-services/setup/overview"
        : "/dashboard";
    } catch (e) {
      setError(e instanceof Error ? e.message : "We couldn't create your workspace. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.wordmark} href="/" aria-label="Fuvay home">
          <span className={styles.wordmarkIcon}>F</span><span>Fuvay</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <span className={styles.headerPrompt} style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Already have an account?</span>
          <Link href="/login" style={{ minHeight: 36, padding: "0 16px", display: "inline-flex", alignItems: "center", border: "1px solid var(--border-strong)", borderRadius: "var(--radius-md)", color: "var(--text-primary)", background: "var(--surface)", fontSize: 14, fontWeight: 600, textDecoration: "none" }}>Sign in</Link>
          <Link href="/help" style={{ fontSize: 13, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>Need help?</Link>
        </div>
      </header>

      <main className={styles.flow}>
        {/* Left rail */}
        <aside className={styles.sidebar} aria-label="Signup progress">
          <Card>
            <h2 style={{ fontSize: 19, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Create your workspace</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 14px" }}>
              Complete these steps to register your business.
            </p>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 10px",
              borderRadius: 999, border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", marginBottom: 18,
            }}>
              <Clock size={13} /> About 4 minutes
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {STEPS.map((s, i) => {
                const state = i < stepIndex ? "done" : i === stepIndex ? "active" : "todo";
                return (
                  <div key={s.id} style={{ display: "flex", gap: 12, paddingBottom: i < STEPS.length - 1 ? 18 : 0, position: "relative" }}>
                    {i < STEPS.length - 1 && (
                      <div style={{
                        position: "absolute", left: 12, top: 26, bottom: 0, width: 2,
                        background: state === "done" ? "var(--brand)" : "var(--border)",
                      }} />
                    )}
                    <div style={{
                      width: 26, height: 26, borderRadius: "50%", flexShrink: 0, zIndex: 1,
                      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700,
                      background: state === "done" ? "var(--brand)" : state === "active" ? "var(--brand)" : "var(--surface)",
                      color: state === "todo" ? "var(--text-tertiary)" : "var(--text-on-brand, #fff)",
                      border: state === "todo" ? "1px solid var(--border)" : "none",
                    }}>
                      {state === "done" ? <CheckCircle2 size={14} /> : i + 1}
                    </div>
                    <div>
                      <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: state === "active" ? "var(--brand)" : "var(--text-primary)" }}>{s.label}</p>
                      <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>{s.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
          <div style={{ marginTop: 14 }}>
            <Card>
              <p style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
                <FileText size={15} /> What happens after signup?
              </p>
              {["Complete your vertical setup", "Submit for admin review", "Activate after approval"].map(t => (
                <p key={t} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 6px" }}>
                  <CheckCircle2 size={13} color="var(--success-text)" /> {t}
                </p>
              ))}
            </Card>
            <div style={{
              marginTop: 14, display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
              borderRadius: "var(--radius-md)", background: "var(--success-bg)", border: "1px solid var(--success-border)",
            }}>
              <ShieldCheck size={15} color="var(--success-text)" />
              <span style={{ fontSize: 12.5, color: "var(--success-text)" }}>No package or payment required now.</span>
            </div>
          </div>
        </aside>

        {/* Right form card */}
        <div className={styles.formPanel}>
          <Card className={styles.formCard} style={{ padding: 28 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-secondary)" }}>Step {stepIndex + 1} of {STEPS.length}</span>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--brand)" }}>{pct}%</span>
            </div>
            <div style={{ height: 5, borderRadius: 999, background: "var(--neutral-bg, var(--border))", overflow: "hidden", marginBottom: 24 }}>
              <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand)", transition: "width 0.25s ease" }} />
            </div>

            {error && <div style={{ marginBottom: 18 }}><Alert tone="danger">{error}</Alert></div>}

            {step.id === "account" && (
              <>
                {TURNSTILE_SITE_KEY && (
                  <Script
                    src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
                    strategy="afterInteractive"
                    onLoad={renderTurnstile}
                  />
                )}
                <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Create your owner account</h1>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: "0 0 24px" }}>
                  Start with your secure login. Business and service setup comes next.
                </p>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Owner details</p>
                <div className={styles.twoColumn} style={{ marginBottom: 16 }}>
                  <Field label="Full name" icon={<User size={16} />} required value={form.owner_name}
                    onChange={v => set("owner_name", v)} placeholder="Enter your full name" autoComplete="name" />
                  <Field label="Mobile number" icon={<Phone size={16} />} type="tel" required value={form.owner_phone}
                    onChange={v => set("owner_phone", v)} placeholder="Enter mobile number" autoComplete="tel" />
                </div>
                <div className={styles.twoColumn} style={{ marginBottom: 16 }}>
                  <Field label="Email address" icon={<Mail size={16} />} type="email" required value={form.owner_email}
                    onChange={v => set("owner_email", v)} placeholder="Enter your email address" autoComplete="email" />
                  <PasswordField label="Password" value={form.password} onChange={v => set("password", v)} placeholder="Create a password" />
                </div>
                {/* Confirm password is full width, not tucked into the
                    right column of the row above -- it stands alone below
                    Email/Password, matching the reference design. */}
                <div style={{ marginBottom: 6 }}>
                  <PasswordField label="Confirm password" value={form.confirmPassword} onChange={v => set("confirmPassword", v)} placeholder="Re-enter your password" />
                </div>
                {form.password && (
                  <div style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    flexWrap: "wrap", gap: 12, margin: "10px 0 4px",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 12, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>Password strength</span>
                      <div style={{ display: "flex", gap: 4 }}>
                        {[0, 1, 2, 3].map(i => (
                          <div key={i} style={{
                            width: 26, height: 4, borderRadius: 2,
                            background: i < pwScore ? (pwScore >= 3 ? "var(--success)" : "var(--warning)") : "var(--border)",
                          }} />
                        ))}
                      </div>
                    </div>
                    {/* Three independent checklist items, each with its own
                        circle marker -- spread across the row rather than
                        run together as one wrapped sentence. */}
                    <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
                      {[
                        { done: form.password.length >= 8, label: "At least 8 characters" },
                        { done: /[a-z]/.test(form.password) && /[A-Z]/.test(form.password), label: "Uppercase and lowercase" },
                        { done: /[0-9]/.test(form.password) || /[^A-Za-z0-9]/.test(form.password), label: "Number or symbol" },
                      ].map(c => (
                        <span key={c.label} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: c.done ? "var(--success-text)" : "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                          {c.done ? <CheckCircle2 size={13} /> : <span style={{ width: 13, height: 13, borderRadius: "50%", border: "1px solid var(--text-tertiary)", display: "inline-block" }} />}
                          {c.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {form.confirmPassword && form.password !== form.confirmPassword && (
                  <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "4px 0 0" }}>Passwords don&apos;t match.</p>
                )}
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "10px 0 0" }}>
                  Your account and workspace are created immediately after contact verification and consent. Admin review happens after business setup.
                </p>
                {TURNSTILE_SITE_KEY && (
                  <div style={{ marginTop: 16 }}>
                    <div ref={turnstileContainerRef} aria-label="Security check" />
                  </div>
                )}
              </>
            )}

            {step.id === "verify" && (
              <>
                <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Verify your contact details</h1>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: "0 0 24px" }}>
                  Enter the codes we sent to your mobile and email to continue.
                </p>
                {devOtps && (
                  <div style={{ marginBottom: 16 }}>
                    <Alert tone="warning" title="Development mode">
                      Real delivery is disabled in this environment. Codes: {Object.entries(devOtps).map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
                    </Alert>
                  </div>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {([
                    { channel: "mobile" as const, icon: <Phone size={16} />, value: form.owner_phone, label: "Mobile number", otp: mobileOtp, setOtp: setMobileOtp, verified: mobileVerified },
                    { channel: "email" as const, icon: <Mail size={16} />, value: form.owner_email, label: "Email", otp: emailOtp, setOtp: setEmailOtp, verified: emailVerified },
                  ]).map(row => (
                    <div key={row.channel} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: 14 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: row.verified ? 0 : 10 }}>
                        {row.icon}
                        <div style={{ flex: 1 }}>
                          <p style={{ margin: 0, fontSize: 13, color: "var(--text-primary)" }}>{row.value || "—"}</p>
                          <p style={{ margin: 0, fontSize: 11.5, color: "var(--text-tertiary)" }}>{row.label}</p>
                        </div>
                        {row.verified && (
                          <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, color: "var(--success-text)", fontWeight: 700 }}>
                            <CheckCircle2 size={15} /> Verified
                          </span>
                        )}
                      </div>
                      {!row.verified && (
                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          <input
                            aria-label={`${row.label} verification code`} inputMode="numeric" autoComplete="one-time-code"
                            value={row.otp} onChange={e => { setError(""); row.setOtp(e.target.value); }} placeholder="Enter code"
                            style={{
                              flex: 1, height: 38, padding: "0 12px", fontSize: 14, background: "var(--surface)",
                              border: "1px solid var(--border)", borderRadius: "var(--radius-md)",
                              color: "var(--text-primary)", outline: "none", fontFamily: "inherit", boxSizing: "border-box",
                            }}
                          />
                          <Button variant="secondary" disabled={otpBusy === row.channel} onClick={() => verifyChannel(row.channel)}>
                            {otpBusy === row.channel ? "Verifying…" : "Verify"}
                          </Button>
                          <button type="button" onClick={() => resendOtp(row.channel)} disabled={otpBusy === row.channel}
                            style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", fontSize: 12.5, color: "var(--brand)", whiteSpace: "nowrap" }}>
                            <RefreshCw size={13} /> Resend
                          </button>
                        </div>
                      )}
                      {!row.verified && otpNotice[row.channel] && (
                        <p role="status" style={{ margin: "8px 0 0", fontSize: 12, color: "var(--success-text)" }}>
                          {otpNotice[row.channel]}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {step.id === "identity" && (
              <>
                <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Business identity</h1>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: "0 0 24px" }}>
                  Legal and location details for your business.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <Field label="Business name" icon={<Building2 size={16} />} required value={form.business_name}
                    onChange={v => set("business_name", v)} placeholder="e.g. Rahul AC Services" />
                  <div className={styles.twoColumn}>
                    <Field label="City" required value={form.city} onChange={v => set("city", v)} placeholder="e.g. Mumbai" />
                    <Field label="State" required value={form.state} onChange={v => set("state", v)} placeholder="e.g. Maharashtra" />
                  </div>
                  <Field label="GSTIN (optional)" value={form.gstin} onChange={v => set("gstin", v)} placeholder="22AAAAA0000A1Z5" />
                  <div>
                    <label htmlFor="business-description" style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                      Business description (optional)
                    </label>
                    <textarea
                      id="business-description"
                      value={form.description} onChange={e => set("description", e.target.value)}
                      placeholder="A short description of the services you offer"
                      rows={3}
                      style={{
                        width: "100%", padding: 12, fontSize: 14, background: "var(--surface)",
                        border: "1px solid var(--border)", borderRadius: "var(--radius-md)",
                        color: "var(--text-primary)", outline: "none", fontFamily: "inherit", resize: "vertical", boxSizing: "border-box",
                      }}
                    />
                  </div>
                </div>
              </>
            )}

            {step.id === "vertical" && (
              <>
                <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Select your vertical</h1>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: "0 0 24px" }}>
                  Choose the business you&apos;re starting with. You can request additional verticals later.
                </p>
                {!verticalsLoaded && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading available verticals…</p>}
                {verticalsLoaded && verticals.length === 0 && (
                  <Alert tone="danger">Couldn&apos;t load available verticals. Please refresh and try again.</Alert>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 10 }}>
                  {verticals.map(v => {
                    const VerticalIcon = VERTICAL_ICONS[v.key] ?? Store;
                    return (
                    <button key={v.key} type="button" aria-pressed={form.vertical === v.key} onClick={() => set("vertical", v.key)}
                      style={{
                        display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6,
                        padding: "14px", borderRadius: "var(--radius-md)", cursor: "pointer", textAlign: "left",
                        border: `1px solid ${form.vertical === v.key ? "var(--brand)" : "var(--border)"}`,
                        background: form.vertical === v.key ? "var(--accent-muted)" : "var(--surface)",
                      }}>
                      <VerticalIcon size={20} aria-hidden="true" color={form.vertical === v.key ? "var(--brand)" : "var(--text-secondary)"}/>
                      <span style={{ fontSize: 13, fontWeight: 600, color: form.vertical === v.key ? "var(--brand)" : "var(--text-primary)" }}>{v.label}</span>
                      {v.description && <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>{v.description}</span>}
                    </button>
                  )})}
                </div>
              </>
            )}

            {step.id === "review" && (
              <>
                <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Review &amp; consent</h1>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: "0 0 20px" }}>
                  Confirm your details before creating your workspace. Business setup is submitted for admin review later.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                  {[
                    ["Owner", form.owner_name], ["Email", form.owner_email], ["Mobile", form.owner_phone],
                    ["Business", form.business_name], ["City", form.city + (form.state ? `, ${form.state}` : "")],
                    ["Vertical", verticals.find(v => v.key === form.vertical)?.label ?? form.vertical ?? "—"],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--text-tertiary)" }}>{k}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v || "—"}</span>
                    </div>
                  ))}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
                    <input type="checkbox" checked={form.authorized} onChange={e => set("authorized", e.target.checked)}
                      style={{ marginTop: 2, width: 16, height: 16, accentColor: "var(--success)" }} />
                    I confirm that I am authorized to create this business account. *
                  </label>
                  <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>
                    <input type="checkbox" checked={form.agreedTerms} onChange={e => set("agreedTerms", e.target.checked)}
                      style={{ marginTop: 2, width: 16, height: 16, accentColor: "var(--success)" }} />
                    I agree to the <Link href="/terms" style={{ color: "var(--brand)" }}>Terms of Service</Link> and acknowledge the <Link href="/privacy" style={{ color: "var(--brand)" }}>Privacy Notice</Link>. *
                  </label>
                  <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13, color: "var(--text-secondary)", cursor: "pointer" }}>
                    <input type="checkbox" checked={form.marketingOptIn} onChange={e => set("marketingOptIn", e.target.checked)}
                      style={{ marginTop: 2, width: 16, height: 16, accentColor: "var(--success)" }} />
                    Send me product updates and business tips. (Optional)
                  </label>
                </div>
              </>
            )}

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 28 }}>
              {stepIndex > 0
                ? <Button variant="ghost" onClick={goBack}><ArrowLeft size={15} style={{ marginRight: 6 }} />Back</Button>
                : <Link href="/login" style={{ fontSize: 13, color: "var(--text-secondary)", textDecoration: "none" }}>Exit</Link>}
              {step.id === "review"
                ? <Button variant="primary" loading={submitting} disabled={submitting} onClick={submit}>
                    {submitting ? "Creating workspace…" : "Create workspace"}
                  </Button>
                : <Button variant="primary" loading={submitting} disabled={submitting} onClick={goNext}>
                    Continue{stepIndex === 0 ? " to verification" : ""} <ArrowRight size={15} style={{ marginLeft: 6 }} />
                  </Button>}
            </div>
            <p style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 7, fontSize: 11.5, color: "var(--text-tertiary)", textAlign: "center", margin: "16px 0 0" }}>
              <Lock size={12} aria-hidden="true" /> Your information is encrypted and saved securely.
            </p>
          </Card>
        </div>
      </main>

      <footer style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 32px", borderTop: "1px solid var(--border)", fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap", gap: 8,
      }}>
        <span>© {new Date().getFullYear()} Fuvay. All rights reserved.</span>
        <div style={{ display: "flex", gap: 16 }}>
          <Link href="/terms" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Terms of Service</Link>
          <Link href="/privacy" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Privacy Notice</Link>
          <Link href="/security" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Security</Link>
        </div>
      </footer>
    </div>
  );
}
