"use client";
import React, { useState, useEffect } from "react";
import { ShieldCheck, Eye, EyeOff, AlertTriangle, Check } from "lucide-react";
import { authApi } from "../../lib/api";

function rule(label: string, ok: boolean) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12,
      color: ok ? "var(--success-text)" : "var(--text-tertiary)" }}>
      <Check size={12} style={{ opacity: ok ? 1 : 0.3 }}/>
      {label}
    </div>
  );
}

export default function ChangePasswordPage() {
  const [current,  setCurrent]  = useState("");
  const [next,     setNext]     = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [showCurr, setShowCurr] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  useEffect(() => {
    const token = localStorage.getItem("serviceos_tenant_token");
    if (!token && typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const hasLen    = next.length >= 8;
  const hasUpper  = /[A-Z]/.test(next);
  const hasNumber = /\d/.test(next);
  const matches   = next.length > 0 && next === confirm;
  const canSubmit = hasLen && hasUpper && hasNumber && matches && current.length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true); setError("");
    try {
      await authApi.changePassword(current, next);
      localStorage.removeItem("serviceos_force_pw_change");
      window.location.href = "/onboarding";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password change failed. Check your current password.");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "var(--bg)", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 440 }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 16px", boxShadow: "var(--shadow-md)" }}>
            <span style={{ color: "white", fontWeight: 800, fontSize: 22 }}>S</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
            Set your password
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Your account was created with a temporary password. Set a permanent one to continue.
          </p>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 16, padding: 32, boxShadow: "var(--shadow-lg)" }}>

          {error && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "12px 14px",
              borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              color: "var(--danger-text)", fontSize: 13, marginBottom: 18, lineHeight: 1.5 }}>
              <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Current (temp) password */}
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)",
                display: "block", marginBottom: 5 }}>Temporary Password</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showCurr ? "text" : "password"}
                  value={current}
                  onChange={e => setCurrent(e.target.value)}
                  required
                  placeholder="Enter the password from your welcome screen"
                  style={{ width: "100%", height: 42, padding: "0 40px 0 14px", fontSize: 14,
                    background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: 10, color: "var(--text-primary)", outline: "none",
                    fontFamily: "inherit", boxSizing: "border-box" as const }}
                  onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                  onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                />
                <button type="button" onClick={() => setShowCurr(v => !v)}
                  style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                    background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)",
                    display: "flex", alignItems: "center" }}>
                  {showCurr ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            {/* New password */}
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)",
                display: "block", marginBottom: 5 }}>New Password</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showNext ? "text" : "password"}
                  value={next}
                  onChange={e => setNext(e.target.value)}
                  required
                  placeholder="Min 8 chars, 1 uppercase, 1 number"
                  style={{ width: "100%", height: 42, padding: "0 40px 0 14px", fontSize: 14,
                    background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: 10, color: "var(--text-primary)", outline: "none",
                    fontFamily: "inherit", boxSizing: "border-box" as const }}
                  onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                  onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                />
                <button type="button" onClick={() => setShowNext(v => !v)}
                  style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                    background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)",
                    display: "flex", alignItems: "center" }}>
                  {showNext ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
              {next.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
                  {rule("At least 8 characters", hasLen)}
                  {rule("At least one uppercase letter", hasUpper)}
                  {rule("At least one number", hasNumber)}
                </div>
              )}
            </div>

            {/* Confirm */}
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)",
                display: "block", marginBottom: 5 }}>Confirm New Password</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                required
                placeholder="Repeat your new password"
                style={{ width: "100%", height: 42, padding: "0 14px", fontSize: 14,
                  background: "var(--surface)",
                  border: `1px solid ${confirm.length > 0 ? (matches ? "var(--success-border)" : "var(--danger-border)") : "var(--border)"}`,
                  borderRadius: 10, color: "var(--text-primary)", outline: "none",
                  fontFamily: "inherit", boxSizing: "border-box" as const }}
              />
              {confirm.length > 0 && !matches && (
                <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "4px 0 0" }}>Passwords do not match</p>
              )}
            </div>

            <button type="submit" disabled={!canSubmit || loading}
              style={{ height: 44, borderRadius: 11, border: "none", background: "var(--brand)",
                color: "white", fontWeight: 600, fontSize: 14,
                cursor: (!canSubmit || loading) ? "not-allowed" : "pointer",
                opacity: (!canSubmit || loading) ? 0.6 : 1,
                fontFamily: "inherit", transition: "opacity 0.15s", marginTop: 4 }}>
              {loading ? "Saving…" : "Set Password & Continue →"}
            </button>
          </form>
        </div>

        <p style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11,
          color: "var(--text-tertiary)", marginTop: 20, justifyContent: "center" }}>
          <ShieldCheck size={13}/> Secured by ServiceOS Auth Engine
        </p>
      </div>
    </div>
  );
}
