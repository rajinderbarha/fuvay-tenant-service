"use client";
/**
 * Login Page — Super Admin Portal
 * PROVEN: calls authApi.login (lib/api.ts) — no inline fetch calls.
 * Mirrors tenant-portal's login page visual design (split marketing panel +
 * sign-in card). Super admins are provisioned internally, never self-signed-up
 * — so unlike the tenant page, there is no "create account" / registration
 * entry point anywhere on this page.
 */
import React, { useState } from "react";
import { Button, Alert } from "@serviceos/design-system";
import {
  Mail, Lock, Eye, EyeOff, ShieldCheck, Building2, Users, Activity,
} from "lucide-react";
import { authApi } from "../../lib/api";

function IconField({
  id, icon: Icon, type, value, onChange, placeholder, focused, onFocus, onBlur, rightSlot,
}: {
  id: string;
  icon: React.ComponentType<{ size?: number }>;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  focused: boolean;
  onFocus: () => void;
  onBlur: () => void;
  rightSlot?: React.ReactNode;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", height: 46, borderRadius: 10,
      border: `1px solid ${focused ? "var(--border-focus)" : "var(--border)"}`,
      background: "var(--surface)", transition: "border-color 0.15s",
      boxShadow: focused ? "0 0 0 3px rgba(59,130,246,0.12)" : "none",
    }}>
      <div style={{ width: 42, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)" }}>
        <Icon size={16} />
      </div>
      <input
        id={id}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={onFocus}
        onBlur={onBlur}
        placeholder={placeholder}
        required
        style={{
          flex: 1, height: "100%", border: "none", outline: "none", background: "transparent",
          color: "var(--text-primary)", fontSize: 14, fontFamily: "inherit", paddingRight: 8,
        }}
      />
      {rightSlot}
    </div>
  );
}

function BackgroundGlyphs() {
  const items = [
    { Icon: ShieldCheck, top: "8%", left: "12%", size: 28 },
    { Icon: Building2, top: "68%", left: "8%", size: 22 },
    { Icon: Users, top: "22%", left: "78%", size: 24 },
    { Icon: Activity, top: "76%", left: "82%", size: 20 },
  ];
  return (
    <div aria-hidden style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      {items.map(({ Icon, top, left, size }, i) => (
        <div key={i} style={{ position: "absolute", top, left, opacity: 0.06, color: "var(--text-primary)" }}>
          <Icon size={size} />
        </div>
      ))}
    </div>
  );
}

function FeatureRow({ icon: Icon, title, description }: { icon: React.ComponentType<{ size?: number }>; title: string; description: string }) {
  return (
    <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
      <div style={{
        width: 36, height: 36, borderRadius: 9, background: "var(--surface)", border: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--brand)",
      }}>
        <Icon size={17} />
      </div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>{title}</div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.4 }}>{description}</div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [focusedField, setFocusedField] = useState<"email" | "password" | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Both fields are required."); return; }
    setLoading(true); setError("");
    try {
      const res = await authApi.login(email, password);
      localStorage.setItem("serviceos_admin_token", res.access_token);
      if (res.refresh_token) localStorage.setItem("serviceos_admin_refresh", res.refresh_token);
      if (res.requires_password_change) {
        window.location.href = "/change-password-required";
      } else {
        window.location.href = "/admin/dashboard";
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg)" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "18px 32px", borderBottom: "1px solid var(--border)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 9, background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "var(--shadow-md)",
          }}>
            <span style={{ color: "white", fontWeight: 800, fontSize: 15 }}>S</span>
          </div>
          <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>ServiceOS</span>
        </div>
        <div style={{
          display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-tertiary)",
          padding: "5px 10px", borderRadius: 999, border: "1px solid var(--border)",
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success-text, #16a34a)" }} />
          Portal reachable
        </div>
      </div>

      {/* Body */}
      <div style={{
        flex: 1, display: "flex", position: "relative", alignItems: "stretch",
        flexWrap: "wrap",
      }}>
        {/* Marketing panel */}
        <div style={{
          flex: "1 1 480px", position: "relative", padding: "64px 48px",
          display: "flex", flexDirection: "column", justifyContent: "center", minHeight: 420,
        }}>
          <BackgroundGlyphs />
          <div style={{ position: "relative", maxWidth: 460 }}>
            <h1 style={{ fontSize: 30, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px", lineHeight: 1.25 }}>
              Platform control, in one place
            </h1>
            <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 32px", lineHeight: 1.6 }}>
              Oversee every tenant, service vertical, and platform-wide operation from a single
              secured console built for the ServiceOS operations team.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 32 }}>
              <FeatureRow icon={Building2} title="Tenant oversight" description="Manage onboarding, plans, and health across every tenant on the platform." />
              <FeatureRow icon={Users} title="Platform-wide access control" description="Provision and audit admin, staff, and support roles from one place." />
              <FeatureRow icon={Activity} title="Real-time operational visibility" description="Monitor bookings, finance, and security signals as they happen." />
            </div>

            <div style={{
              display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderRadius: 10,
              background: "var(--success-bg)", border: "1px solid var(--success-border)", color: "var(--success-text)",
              fontSize: 13,
            }}>
              <ShieldCheck size={16} />
              Protected by role-based access, audit logging, and session controls.
            </div>
          </div>
        </div>

        {/* Sign-in card */}
        <div style={{
          flex: "1 1 420px", display: "flex", alignItems: "center", justifyContent: "center",
          padding: "48px 32px", borderLeft: "1px solid var(--border)", background: "var(--surface)",
        }}>
          <div style={{ width: "100%", maxWidth: 380 }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: "var(--brand)", marginBottom: 8 }}>
              SUPER ADMIN
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Welcome back
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 24px" }}>
              Sign in with your administrator credentials to continue.
            </p>

            {error && <div style={{ marginBottom: 16 }}><Alert tone="danger" title="Sign in failed">{error}</Alert></div>}

            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label htmlFor="admin-email" style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                  Email Address
                </label>
                <IconField
                  id="admin-email"
                  icon={Mail}
                  type="email"
                  value={email}
                  onChange={setEmail}
                  placeholder="you@serviceos.in"
                  focused={focusedField === "email"}
                  onFocus={() => setFocusedField("email")}
                  onBlur={() => setFocusedField(null)}
                />
              </div>
              <div>
                <label htmlFor="admin-password" style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                  Password
                </label>
                <IconField
                  id="admin-password"
                  icon={Lock}
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={setPassword}
                  placeholder="••••••••••"
                  focused={focusedField === "password"}
                  onFocus={() => setFocusedField("password")}
                  onBlur={() => setFocusedField(null)}
                  rightSlot={
                    <button
                      type="button"
                      onClick={() => setShowPassword(s => !s)}
                      style={{
                        border: "none", background: "transparent", cursor: "pointer",
                        color: "var(--text-tertiary)", padding: "0 12px", display: "flex", alignItems: "center",
                      }}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  }
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <a href="/forgot-password" style={{ fontSize: 12.5, color: "var(--brand)", textDecoration: "none" }}>
                  Forgot password?
                </a>
              </div>

              <Button type="submit" variant="primary" disabled={loading} style={{ width: "100%", height: 44 }}>
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            <p style={{
              fontSize: 11.5, color: "var(--text-tertiary)", margin: "24px 0 0", textAlign: "center",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}>
              <Lock size={12} />
              Secured by ServiceOS Auth Engine · JWT + TOTP
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: "16px 32px", borderTop: "1px solid var(--border)", display: "flex",
        justifyContent: "space-between", flexWrap: "wrap", gap: 8, fontSize: 12, color: "var(--text-tertiary)",
      }}>
        <span>© {new Date().getFullYear()} ServiceOS. All rights reserved.</span>
        <div style={{ display: "flex", gap: 16 }}>
          <a href="/terms" style={{ color: "inherit", textDecoration: "none" }}>Terms</a>
          <a href="/privacy" style={{ color: "inherit", textDecoration: "none" }}>Privacy</a>
          <a href="/security" style={{ color: "inherit", textDecoration: "none" }}>Security</a>
        </div>
      </div>
    </div>
  );
}
