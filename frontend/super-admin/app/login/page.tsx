"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Alert, Button } from "@serviceos/design-system";
import {
  Activity, ArrowLeft, CheckCircle2, Eye, EyeOff, KeyRound, Lock,
  Mail, ShieldCheck, UserRoundCheck,
} from "lucide-react";
import { authApi, type AdminUser } from "../../lib/api";
import FuvayLogo from "../../components/brand/FuvayLogo";

const PLATFORM_ADMIN_ROLES = new Set([
  "super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly",
]);

type LoginStep = "credentials" | "mfa";

function LoginField({
  id, label, icon: Icon, type, value, onChange, placeholder, autoComplete, inputMode, maxLength, rightSlot,
}: {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  type: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoComplete: string;
  inputMode?: "numeric";
  maxLength?: number;
  rightSlot?: React.ReactNode;
}) {
  return (
    <div className="admin-login-field-group">
      <label htmlFor={id}>{label}</label>
      <div className="admin-login-field">
        <Icon size={17} aria-hidden="true" />
        <input
          id={id}
          type={type}
          value={value}
          onChange={event => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          inputMode={inputMode}
          maxLength={maxLength}
          required
        />
        {rightSlot}
      </div>
    </div>
  );
}

function Capability({ icon: Icon, title, description }: {
  icon: React.ComponentType<{ size?: number }>;
  title: string;
  description: string;
}) {
  return (
    <div className="admin-login-capability">
      <span className="admin-login-capability-icon"><Icon size={18} /></span>
      <span>
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
    </div>
  );
}

export default function LoginPage() {
  const [step, setStep] = useState<LoginStep>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaChallenge, setMfaChallenge] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [platformOnline, setPlatformOnline] = useState<boolean | null>(null);

  useEffect(() => {
    authApi.health()
      .then(result => setPlatformOnline(result.status === "ok" || result.status === "healthy"))
      .catch(() => setPlatformOnline(false));
  }, []);

  async function rejectNonAdmin(user?: AdminUser, accessToken?: string) {
    if (user && PLATFORM_ADMIN_ROLES.has(user.role)) return false;
    if (accessToken) {
      localStorage.setItem("serviceos_admin_token", accessToken);
      await authApi.logout().catch(() => undefined);
    }
    localStorage.removeItem("serviceos_admin_token");
    localStorage.removeItem("serviceos_admin_refresh");
    setError("This account does not have access to the ServiceOS Admin Control Center.");
    return true;
  }

  async function establishAdminSession(result: {
    access_token?: string;
    refresh_token?: string | null;
    user?: AdminUser;
    requires_password_change?: boolean;
  }) {
    if (!result.access_token || await rejectNonAdmin(result.user, result.access_token)) return;
    localStorage.setItem("serviceos_admin_token", result.access_token);
    if (result.refresh_token) localStorage.setItem("serviceos_admin_refresh", result.refresh_token);
    else localStorage.removeItem("serviceos_admin_refresh");
    window.location.href = result.requires_password_change
      ? "/change-password-required"
      : "/admin/dashboard";
  }

  async function handleCredentials(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your administrator email and password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await authApi.login(email.trim(), password);
      if (result.mfa_required) {
        if (!result.mfa_challenge_token) throw new Error("The MFA challenge could not be started. Sign in again.");
        setMfaChallenge(result.mfa_challenge_token);
        setStep("mfa");
        return;
      }
      await establishAdminSession(result);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Sign-in failed. Check your credentials and try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMfa(event: React.FormEvent) {
    event.preventDefault();
    const cleanCode = mfaCode.trim();
    if (cleanCode.length < 6) {
      setError("Enter the 6-digit authenticator code or a valid backup code.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await authApi.verifyMfa(mfaChallenge, cleanCode);
      await establishAdminSession(result);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Verification failed. Check the code and try again.");
    } finally {
      setLoading(false);
    }
  }

  function backToCredentials() {
    setStep("credentials");
    setMfaCode("");
    setMfaChallenge("");
    setError("");
  }

  return (
    <main className="admin-login-page">
      <section className="admin-login-shell" aria-label="Fuvay administrator sign in">
        <aside className="admin-login-command-panel">
          <div className="admin-login-brand">
            {/* .admin-login-command-panel is a dark gradient with white text
                in both themes, so it needs the white-wordmark artwork. */}
            <FuvayLogo height={46} tone="onDark"/>
            <span>
              <small>Admin Control Center</small>
            </span>
          </div>

          <div className="admin-login-command-copy">
            <span className="admin-login-eyebrow"><ShieldCheck size={14} /> Platform administration</span>
            <h1>Operate the entire platform with clarity.</h1>
            <p>
              A secured command surface for tenant operations, service governance,
              finance oversight and platform risk.
            </p>
            <div className="admin-login-capabilities">
              <Capability icon={UserRoundCheck} title="Controlled administrator access" description="Role-scoped tools and approval boundaries." />
              <Capability icon={Activity} title="Live operational context" description="Cross-platform health, jobs and finance signals." />
              <Capability icon={KeyRound} title="Audited sensitive actions" description="Traceable changes with session protection." />
            </div>
          </div>

          <div className="admin-login-trust">
            <span className="admin-login-trust-icon"><ShieldCheck size={17} /></span>
            <span><strong>Authorized personnel only</strong><small>Access attempts and administrative actions are recorded.</small></span>
          </div>
        </aside>

        <div className="admin-login-form-panel">
          <div className="admin-login-status" role="status">
            <span className={platformOnline === false ? "is-offline" : platformOnline ? "is-online" : "is-checking"} />
            {platformOnline === false ? "Platform status unavailable" : platformOnline ? "Platform operational" : "Checking platform"}
          </div>

          <div className="admin-login-form-wrap">
            {step === "mfa" && (
              <button type="button" className="admin-login-back" onClick={backToCredentials}>
                <ArrowLeft size={15} /> Back to sign in
              </button>
            )}

            <span className="admin-login-form-icon">
              {step === "credentials" ? <Lock size={21} /> : <ShieldCheck size={21} />}
            </span>
            <p className="admin-login-form-kicker">ADMIN CONTROL CENTER</p>
            <h2>{step === "credentials" ? "Administrator sign in" : "Verify your identity"}</h2>
            <p className="admin-login-form-description">
              {step === "credentials"
                ? "Use your provisioned platform administrator account."
                : `Enter the authenticator code for ${email}.`}
            </p>

            {error && <Alert tone="danger" title="Access not granted">{error}</Alert>}

            {step === "credentials" ? (
              <form onSubmit={handleCredentials} className="admin-login-form" noValidate>
                <LoginField
                  id="admin-email" label="Work email" icon={Mail} type="email" value={email}
                  onChange={setEmail} placeholder="admin@serviceos.in" autoComplete="username"
                />
                <LoginField
                  id="admin-password" label="Password" icon={Lock} type={showPassword ? "text" : "password"}
                  value={password} onChange={setPassword} placeholder="Enter your password" autoComplete="current-password"
                  rightSlot={(
                    <button type="button" className="admin-login-password-toggle"
                      onClick={() => setShowPassword(value => !value)}
                      aria-label={showPassword ? "Hide password" : "Show password"}>
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  )}
                />
                <div className="admin-login-form-meta">
                  <span><CheckCircle2 size={14} /> Encrypted connection</span>
                  <Link href="/forgot-password">Forgot password?</Link>
                </div>
                <Button type="submit" variant="primary" size="lg" loading={loading} className="admin-login-submit">
                  Continue securely
                </Button>
              </form>
            ) : (
              <form onSubmit={handleMfa} className="admin-login-form" noValidate>
                <LoginField
                  id="admin-mfa-code" label="Authenticator or backup code" icon={KeyRound} type="text"
                  value={mfaCode} onChange={value => setMfaCode(value.replace(/\s/g, ""))}
                  placeholder="Enter verification code" autoComplete="one-time-code" inputMode="numeric" maxLength={8}
                />
                <Button type="submit" variant="primary" size="lg" loading={loading} className="admin-login-submit">
                  Verify and continue
                </Button>
              </form>
            )}

            <p className="admin-login-help">
              Need administrator access? Contact your Fuvay platform owner.
            </p>
          </div>
        </div>
      </section>

      <footer className="admin-login-footer">
        <span>© {new Date().getFullYear()} Fuvay</span>
        <span>Protected by session controls, MFA and audit logging</span>
      </footer>
    </main>
  );
}
