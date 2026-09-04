"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Alert } from "@serviceos/design-system";
import { ArrowRight, Eye, EyeOff, Lock, Mail, ShieldCheck, Smartphone, UserCheck, Wrench } from "lucide-react";
import { authApi, publicSignupStatusApi } from "../../lib/api";
import styles from "./login.module.css";

const FEATURES = [
  { icon: Wrench, title: "Vertical-isolated operations", description: "Each business vertical keeps its own setup and activity." },
  { icon: UserCheck, title: "Verified business access", description: "Only authorized owners and team members can sign in." },
  { icon: ShieldCheck, title: "Secure owner workspace", description: "Role-based access, session controls and audited activity." },
] as const;

type FieldProps = { id: string; label: string; type: string; value: string; placeholder: string; autoComplete: string; icon: React.ReactNode; onChange: (value: string) => void; trailing?: React.ReactNode; inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"] };

function LoginField({ id, label, type, value, placeholder, autoComplete, icon, onChange, trailing, inputMode }: FieldProps) {
  return <label className={styles.field} htmlFor={id}>
    <span className={styles.fieldLabel}>{label}</span>
    <span className={styles.fieldControl}>
      <span className={styles.fieldIcon} aria-hidden="true">{icon}</span>
      <input id={id} type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder}
        autoComplete={autoComplete} inputMode={inputMode} required className={styles.input} />
      {trailing}
    </span>
  </label>;
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    if (!email || !password) { setError("Both fields required."); return; }
    setLoading(true); setError("");
    try {
      const response = await authApi.login(email, password);
      localStorage.setItem("serviceos_tenant_token", response.access_token);
      if (response.refresh_token) localStorage.setItem("serviceos_tenant_refresh", response.refresh_token);
      localStorage.setItem("serviceos_remember_device", remember ? "1" : "0");
      const user = response.user;
      localStorage.setItem("serviceos_user_id", user?.id ?? user?.user_id ?? "");
      localStorage.setItem("serviceos_tenant_id", user?.tenant_id ?? "");
      localStorage.setItem("serviceos_user_role", user?.role ?? "");
      localStorage.setItem("serviceos_tenant_name", user?.full_name ?? "");
      const tenant = response.tenant;
      localStorage.setItem("serviceos_tenant_vertical", tenant?.vertical ?? "");
      localStorage.setItem("serviceos_tenant_health", String(tenant?.health_score ?? 0));
      if (tenant?.name) localStorage.setItem("serviceos_tenant_name", tenant.name);
      if (response.requires_password_change || user?.force_password_change) {
        localStorage.setItem("serviceos_force_pw_change", "1");
        window.location.href = "/change-password-required";
        return;
      }
      localStorage.removeItem("serviceos_force_pw_change");
      const routes: Record<string, string> = { vertical_setup_wizard: "/tenant/home-services/setup/overview", application_status: "/onboarding/application-status", activation_center: "/onboarding/activation-center", tenant_dashboard: "/dashboard", resume_signup: "/register", restricted_account: "/help" };
      const projectedRoute = response.next_destination ? routes[response.next_destination] : undefined;
      window.location.href = projectedRoute ?? (!user?.onboarding_complete && tenant?.vertical === "home_services" ? "/tenant/home-services/setup/overview" : "/dashboard");
    } catch (loginError: unknown) {
      let message = loginError instanceof Error ? loginError.message : "Login failed. Check credentials.";
      try {
        const status = await publicSignupStatusApi.lookupByEmail(email);
        if (status.exists && status.status !== "activated") message = status.status === "rejected"
          ? "Your business signup request was not approved. Contact support for details."
          : "Your signup request is still under review. You'll receive your login details by email once it's approved.";
      } catch { /* Keep the authentication error. */ }
      setError(message);
    } finally { setLoading(false); }
  }

  return <main className={styles.page}>
    <section className={styles.storyPanel} aria-labelledby="login-story-title">
      <div className={styles.glowTop} aria-hidden="true" /><div className={styles.glowBottom} aria-hidden="true" />
      <div className={styles.storyIntro}>
        <Link className={styles.wordmark} href="/" aria-label="Fuvay home"><span className={styles.wordmarkIcon}>F</span><span>Fuvay</span></Link>
        <div className={styles.storyCopy}>
          <p className={styles.eyebrow}>Tenant portal</p>
          <h1 id="login-story-title">Run every service business from one workspace.</h1>
          <p className={styles.storyDescription}>Home Services, Coaching, Real Estate and future verticals — each isolated, each fully under your control.</p>
        </div>
      </div>
      <div className={styles.featureList}>{FEATURES.map(({ icon: Icon, title, description }) =>
        <div className={styles.feature} key={title}>
          <span className={styles.featureIcon} aria-hidden="true"><Icon size={17} /></span>
          <span className={styles.featureCopy}><strong>{title}</strong><span>{description}</span></span>
        </div>)}</div>
    </section>

    <section className={styles.formPanel} aria-labelledby="login-heading">
      <nav className={styles.utilityNav} aria-label="Account help"><span>Need help?</span></nav>
      <div className={styles.formStage}><div className={styles.formWrap}>
        <header className={styles.formHeader}><h2 id="login-heading">Welcome back</h2>
          <p>Sign in to continue managing your business. You&apos;ll be taken to your current setup, review or active workspace.</p></header>
        {error && <Alert tone="danger" title="Sign in failed">{error}</Alert>}
        <form className={styles.form} onSubmit={handleLogin}>
          <LoginField id="tenant-identifier" label="Email or mobile number" type="text" inputMode="email" autoComplete="username"
            value={email} onChange={setEmail} placeholder="provider@servicesos.in" icon={<Mail size={16} />} />
          <LoginField id="tenant-password" label="Password" type={showPassword ? "text" : "password"} autoComplete="current-password"
            value={password} onChange={setPassword} placeholder="••••••••••" icon={<Lock size={16} />}
            trailing={<button className={styles.visibilityButton} type="button" onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button>} />
          <div className={styles.formOptions}>
            <label className={styles.rememberOption}><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /><span>Remember this device</span></label>
            <Link href="/forgot-password">Forgot password?</Link>
          </div>
          <button className={styles.submitButton} type="submit" disabled={loading}><span>{loading ? "Signing in…" : "Sign in"}</span>{!loading && <ArrowRight size={16} aria-hidden="true" />}</button>
          <div className={styles.divider} aria-hidden="true"><span /><b>or</b><span /></div>
          <button className={styles.otpButton} type="button" disabled title="Mobile OTP sign-in isn't available yet"><Smartphone size={16} aria-hidden="true" />Continue with mobile OTP</button>
        </form>
        <div className={styles.accountLinks}>
          <p>New to Fuvay? <Link href="/register">Create business account</Link></p>
          <p className={styles.securityNote}><Lock size={12} aria-hidden="true" />Your login activity and device sessions are monitored for security.</p>
        </div>
      </div></div>
      <footer className={styles.footer}><Link href="/terms">Terms of Service</Link><Link href="/privacy">Privacy Policy</Link><Link href="/security">Security</Link></footer>
    </section>
  </main>;
}
