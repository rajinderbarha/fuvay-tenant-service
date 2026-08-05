"use client";
/**
 * Tenant Login Page.
 * PROVEN: authApi.login() from lib/api.ts — no inline fetch calls.
 * Stores token + full tenant context in localStorage on success.
 *
 * Layout matches the approved external design (split marketing panel +
 * sign-in card) — that design was supplied as reference images, not files
 * in this repo (confirmed: the exact copy never appears anywhere in git
 * history or on disk). Rebuilt here directly against those references.
 * Every visual element maps to something real; nothing here fakes data.
 */
import React, { useState } from "react";
import Link from "next/link";
import { Button, Alert } from "@serviceos/design-system";
import { authApi, categoryDashboardApi, publicSignupStatusApi } from "../../lib/api";
import {
  Mail, Lock, Eye, EyeOff, Smartphone, Wrench, UserCheck, ShieldCheck, Lock as LockIcon,
  Home, ClipboardList, User as UserIcon, Building2, UtensilsCrossed, Briefcase,
} from "lucide-react";

/** Icon-prefixed text field with a bordered "icon cell" separated from the
 * input by a divider, matching the reference design's field style (a
 * distinct icon compartment, not just a floating glyph). The design-system
 * `Input` has no icon slot, so this wraps it in local markup rather than
 * forking the shared component for one page's visual need. */
function IconField({
  icon, type, value, onChange, placeholder, autoComplete, trailing,
}: {
  icon: React.ReactNode; type: string; value: string;
  onChange: (v: string) => void; placeholder: string; autoComplete: string;
  trailing?: React.ReactNode;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{
      position: "relative", display: "flex", alignItems: "center", height: 46,
      background: "var(--surface)", border: `1px solid ${focused ? "var(--border-focus)" : "var(--border)"}`,
      borderRadius: "var(--radius-md)", overflow: "hidden", transition: "border-color 0.15s ease",
    }}>
      <span style={{
        display: "flex", alignItems: "center", justifyContent: "center", width: 42, height: "100%",
        color: "var(--text-tertiary)", borderRight: "1px solid var(--border)", flexShrink: 0,
      }}>
        {icon}
      </span>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          flex: 1, height: "100%", padding: `0 ${trailing ? 40 : 14}px 0 12px`, fontSize: 14,
          background: "transparent", border: "none", color: "var(--text-primary)",
          outline: "none", fontFamily: "inherit", boxSizing: "border-box", minWidth: 0,
        }}
      />
      {trailing && <span style={{ position: "absolute", right: 14, display: "flex" }}>{trailing}</span>}
    </div>
  );
}

/** Faint outline icons scattered behind the marketing panel, matching the
 * reference design's decorative watermark layer. Purely ornamental --
 * `aria-hidden` and pointer-events disabled so they never intercept clicks
 * or get announced to screen readers. */
function BackgroundGlyphs() {
  const glyphs: { Icon: React.ComponentType<{ size?: number }>; top: string; left: string; size: number; rotate?: number }[] = [
    { Icon: Home,              top: "6%",  left: "2%",  size: 64, rotate: -6 },
    { Icon: ClipboardList,     top: "18%", left: "92%", size: 46, rotate: 8 },
    { Icon: UserIcon,          top: "48%", left: "1%",  size: 40 },
    { Icon: Building2,         top: "78%", left: "90%", size: 56, rotate: 4 },
    { Icon: UtensilsCrossed,   top: "82%", left: "6%",  size: 34 },
    { Icon: Briefcase,         top: "40%", left: "94%", size: 30 },
  ];
  return (
    <div aria-hidden style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
      {glyphs.map((g, i) => (
        <div key={i} style={{
          position: "absolute", top: g.top, left: g.left,
          transform: `rotate(${g.rotate ?? 0}deg)`, color: "var(--text-tertiary)", opacity: 0.08,
        }}>
          <g.Icon size={g.size} />
        </div>
      ))}
    </div>
  );
}

/** Solid-brand or outline-brand button in the exact orange the reference
 * design uses for its two CTAs -- the design-system's `secondary` variant
 * is a neutral outline, which doesn't match either "Sign in" (solid) or
 * "Create business account" (brand-coloured outline) here. */
function BrandOutlineLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      height: 38, padding: "0 18px", borderRadius: "var(--radius-md)",
      border: "1px solid var(--brand)", color: "var(--brand)", fontWeight: 700, fontSize: 13.5,
      textDecoration: "none", whiteSpace: "nowrap",
    }}>
      {children}
    </Link>
  );
}

function FeatureRow({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
      <div style={{
        width: 44, height: 44, borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "center", color: "var(--brand)", flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{title}</p>
        <p style={{ margin: "2px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>{desc}</p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  // Empty by default -- this used to prefill a real working credential
  // pair, which handed a valid account to anyone who opened the page.
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPw,   setShowPw]   = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Both fields required."); return; }
    setLoading(true); setError("");
    try {
      const res = await authApi.login(email, password);
      localStorage.setItem("serviceos_tenant_token", res.access_token);
      if (res.refresh_token) localStorage.setItem("serviceos_tenant_refresh", res.refresh_token);
      // "Remember this device" governs refresh-token retention going
      // forward; it never widens what a single session can already do.
      localStorage.setItem("serviceos_remember_device", remember ? "1" : "0");

      const u = res.user;
      localStorage.setItem("serviceos_user_id",         u?.id ?? u?.user_id ?? "");
      localStorage.setItem("serviceos_tenant_id",       u?.tenant_id ?? "");
      // FINAL-L5-01D fix: role was never persisted, so no page could ever
      // detect a read-only user client-side (ReadOnlyBanner/isReadOnly()
      // had nothing to read). See FINAL_L5_01D_TENANT_READONLY_UX_REPORT.md.
      localStorage.setItem("serviceos_user_role",       u?.role ?? "");
      localStorage.setItem("serviceos_tenant_name",     u?.full_name ?? "");
      localStorage.setItem("serviceos_tenant_vertical", "");
      localStorage.setItem("serviceos_tenant_plan",     "");
      localStorage.setItem("serviceos_tenant_health",   "0");

      try {
        const rt = await categoryDashboardApi.getRuntime() as unknown as Record<string, unknown>;
        const tenant = rt?.tenant as Record<string, unknown> | undefined;
        const tenantName = tenant?.business_name ?? rt?.tenant_name;
        if (rt?.category_type) localStorage.setItem("serviceos_tenant_vertical", String(rt.category_type));
        if (tenantName)         localStorage.setItem("serviceos_tenant_name",     String(tenantName));
        if (rt?.tenant_plan)    localStorage.setItem("serviceos_tenant_plan",     String(rt.tenant_plan));
        if (rt?.tenant_health != null) localStorage.setItem("serviceos_tenant_health", String(rt.tenant_health));
      } catch { /* non-critical */ }

      if (res.requires_password_change || u?.force_password_change) {
        localStorage.setItem("serviceos_force_pw_change", "1");
        window.location.href = "/change-password-required";
      } else {
        localStorage.removeItem("serviceos_force_pw_change");
        // A tenant whose vertical setup isn't complete goes straight back
        // into the setup wizard rather than a dashboard that has nothing
        // to show yet -- only home_services has a built wizard today.
        const vertical = res.tenant?.vertical;
        if (!u?.onboarding_complete && vertical === "home_services") {
          window.location.href = "/tenant/home-services/setup/overview";
        } else {
          window.location.href = "/dashboard";
        }
      }
    } catch (e: unknown) {
      // Real bug fixed here: a "wrong password" message is misleading for
      // someone who signed up through the no-payment request flow, since
      // that flow creates no user account at all until an admin approves
      // it. Login had no way to tell the two cases apart, so every pending
      // applicant saw "Invalid email or password" and had no way to know
      // their password was never the problem.
      let message = e instanceof Error ? e.message : "Login failed. Check credentials.";
      try {
        const status = await publicSignupStatusApi.lookupByEmail(email);
        if (status.exists && status.status !== "activated") {
          message = status.status === "rejected"
            ? "Your business signup request was not approved. Contact support for details."
            : "Your signup request is still under review. You'll receive your login details by email once it's approved.";
        }
      } catch {
        // The lookup itself must never mask the original login error.
      }
      setError(message);
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg)" }}>
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "18px 32px", borderBottom: "1px solid var(--border)", flexWrap: "wrap", gap: 12,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: "var(--radius-md)", background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ color: "var(--text-on-brand, #fff)", fontWeight: 800, fontSize: 14 }}>S</span>
          </div>
          <span style={{ fontWeight: 800, fontSize: 17, color: "var(--text-primary)" }}>ServiceOS</span>
          {/*
            "All systems operational" in the reference design implies a real,
            monitored status feed. No public system-status endpoint exists
            (checked the live schema) -- showing this as a hardcoded "green"
            claim would be exactly the kind of fake-success indicator this
            project has spent this session removing. Reachability of THIS
            page is real signal in itself (a down API would fail login
            below), so the badge reflects that instead of an invented feed.
          */}
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 6, marginLeft: 10,
            padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)",
            background: "var(--bg-muted, transparent)", fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)",
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--text-tertiary)" }} />
            Portal reachable
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>New to ServiceOS?</span>
          <BrandOutlineLink href="/register">Create business account</BrandOutlineLink>
          <Link href="/help" style={{ fontSize: 13, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>
            Need help?
          </Link>
        </div>
      </header>

      {/* ── Split content ────────────────────────────────────────────────── */}
      <div style={{
        position: "relative", flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
        gap: 64, padding: "56px 32px", flexWrap: "wrap", maxWidth: 1280, margin: "0 auto", width: "100%",
      }}>
        <BackgroundGlyphs />
        {/* Marketing panel */}
        <div style={{ flex: "1 1 420px", maxWidth: 520, position: "relative", zIndex: 1 }}>
          <h1 style={{ fontSize: 40, lineHeight: 1.15, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 16px" }}>
            Run every service business from one workspace.
          </h1>
          <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 32px", lineHeight: 1.6 }}>
            Manage Home Services, Coaching, Real Estate and future business verticals independently.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <FeatureRow icon={<Wrench size={20} />} title="Vertical-isolated operations"
              desc="Each business vertical keeps its own setup and activity." />
            <FeatureRow icon={<UserCheck size={20} />} title="Verified business access"
              desc="Only authorized owners and team members can sign in." />
            <FeatureRow icon={<ShieldCheck size={20} />} title="Secure owner workspace"
              desc="Role-based access, session controls and audited activity." />
          </div>
          <div style={{
            marginTop: 28, display: "flex", alignItems: "center", gap: 10,
            padding: "12px 16px", borderRadius: "var(--radius-md)",
            background: "var(--success-bg)", border: "1px solid var(--success-border)",
          }}>
            <ShieldCheck size={16} color="var(--success-text)" />
            <span style={{ fontSize: 13, color: "var(--success-text)" }}>
              Protected by role-based access and monitored sessions.
            </span>
          </div>
        </div>

        {/* Sign-in card */}
        <div style={{
          flex: "1 1 380px", maxWidth: 440, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: "var(--radius-xl, 1rem)",
          padding: 32, boxShadow: "var(--shadow-lg)", position: "relative", zIndex: 1,
        }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px" }}>
            TENANT PORTAL
          </p>
          <h2 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 8px" }}>
            Welcome back
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 4px" }}>
            Sign in to continue managing your business.
          </p>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 22px" }}>
            You&apos;ll be taken to your current setup, review or active workspace.
          </p>

          {error && <div style={{ marginBottom: 16 }}><Alert tone="danger" title="Sign in failed">{error}</Alert></div>}

          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                Email or mobile number
              </label>
              <IconField
                icon={<Mail size={16} />} type="email" autoComplete="username"
                value={email} onChange={setEmail} placeholder="Enter your email or mobile number"
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                Password
              </label>
              <IconField
                icon={<Lock size={16} />} type={showPw ? "text" : "password"} autoComplete="current-password"
                value={password} onChange={setPassword} placeholder="Enter your password"
                trailing={
                  <button type="button" onClick={() => setShowPw(s => !s)} aria-label={showPw ? "Hide password" : "Show password"}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: -4 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)", cursor: "pointer" }}>
                <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: "var(--brand)" }} />
                Remember this device
              </label>
              <Link href="/forgot-password" style={{ fontSize: 13, color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>
                Forgot password?
              </Link>
            </div>

            <Button type="submit" variant="primary" loading={loading} disabled={loading} style={{ height: 46 }}>
              {loading ? "Signing in…" : "Sign in →"}
            </Button>
          </form>

          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "22px 0" }}>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>or</span>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
          </div>

          {/*
            "Continue with mobile OTP" — no OTP-login backend route exists
            (checked the live schema: only the paid signup flow has an OTP
            step, and it is not a login mechanism). Rather than fake a
            working button, this is disabled with an explicit reason so it
            reads as "not yet", not "broken".
          */}
          <button
            type="button"
            disabled
            title="Mobile OTP sign-in isn't available yet"
            style={{
              width: "100%", height: 46, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg-muted, transparent)",
              color: "var(--text-tertiary)", fontWeight: 600, fontSize: 14, cursor: "not-allowed",
            }}
          >
            <Smartphone size={16} /> Continue with mobile OTP
          </button>

          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "20px 0 0", textAlign: "center" }}>
            New to ServiceOS?{" "}
            <Link href="/register" style={{ color: "var(--brand)", fontWeight: 700, textDecoration: "none" }}>
              Create business account
            </Link>
          </p>
          <div style={{
            marginTop: 16, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            fontSize: 12, color: "var(--text-tertiary)",
          }}>
            <LockIcon size={12} />
            Your login activity and device sessions are monitored for security.
          </div>
        </div>
      </div>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 32px", borderTop: "1px solid var(--border)", fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap", gap: 8,
      }}>
        <span>© ServiceOS</span>
        <div style={{ display: "flex", gap: 16 }}>
          <Link href="/terms" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Terms of Service</Link>
          <Link href="/privacy" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Privacy Policy</Link>
          <Link href="/security" style={{ color: "var(--text-tertiary)", textDecoration: "none" }}>Security</Link>
        </div>
      </footer>
    </div>
  );
}
