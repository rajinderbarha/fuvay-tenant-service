"use client";
import React, { useState, useEffect } from "react";
import { authApi } from "../../lib/api";

const RULES = [
  { re: /.{8,}/, label: "At least 8 characters" },
  { re: /[A-Z]/, label: "One uppercase letter" },
  { re: /[a-z]/, label: "One lowercase letter" },
  { re: /[0-9]/, label: "One number" },
  { re: /[!@#$%^&*()\-_=+\[\]{}|;':",.<>?/`~\\]/, label: "One special character" },
];

export default function ChangePasswordRequiredPage() {
  const [current, setCurrent]     = useState("");
  const [next, setNext]           = useState("");
  const [confirm, setConfirm]     = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [success, setSuccess]     = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("serviceos_tenant_token");
    if (!token) window.location.href = "/login";
  }, []);

  function logout() {
    ["serviceos_tenant_token","serviceos_tenant_refresh","serviceos_tenant_id","serviceos_tenant_name",
     "serviceos_tenant_vertical","serviceos_tenant_plan","serviceos_tenant_health","serviceos_user_id",
     "serviceos_force_pw_change"].forEach(k => localStorage.removeItem(k));
    window.location.href = "/login";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!current || !next || !confirm) { setError("All fields are required."); return; }
    if (next !== confirm) { setError("New passwords do not match."); return; }
    const failed = RULES.filter(r => !r.re.test(next));
    if (failed.length) { setError("Password must meet all requirements."); return; }

    setLoading(true); setError("");
    try {
      await authApi.changePasswordRequired(current, next, confirm);
      setSuccess(true);
      // Clear session — must log in again with new password
      ["serviceos_tenant_token","serviceos_tenant_refresh","serviceos_force_pw_change"].forEach(k =>
        localStorage.removeItem(k));
      setTimeout(() => { window.location.href = "/login"; }, 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password change failed. Check your current password.");
    } finally {
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", height: 42, padding: "0 14px", fontSize: 14,
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: 10, color: "var(--text-primary)", outline: "none",
    fontFamily: "inherit", boxSizing: "border-box",
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg)", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 440 }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ width: 52, height: 52, borderRadius: 13, background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 14px", boxShadow: "var(--shadow-md)" }}>
            <span style={{ color: "white", fontWeight: 800, fontSize: 20 }}>S</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>ServiceOS</h1>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Tenant Owner Portal</p>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-xl, 1rem)",
          padding: 32, boxShadow: "var(--shadow-lg)" }}>

          <div style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Password Change Required
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
              Your account requires a password change before you can access your dashboard.
              This may be because a temporary password was set or your password policy requires renewal.
            </p>
          </div>

          {success ? (
            <div style={{ padding: "16px 18px", borderRadius: 10, background: "var(--success-bg)",
              border: "1px solid var(--success-border)", color: "var(--success-text)", fontSize: 14, textAlign: "center" }}>
              Password changed successfully. Redirecting to login…
            </div>
          ) : (
            <>
              {error && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)",
                  border: "1px solid var(--danger-border)", color: "var(--danger-text)",
                  fontSize: 13, marginBottom: 16 }}>{error}</div>
              )}

              <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                    Current / Temporary Password
                  </label>
                  <input type="password" value={current} onChange={e => setCurrent(e.target.value)}
                    placeholder="Your current or temporary password" required style={inputStyle}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                    New Password
                  </label>
                  <input type="password" value={next} onChange={e => setNext(e.target.value)}
                    placeholder="Choose a strong new password" required style={inputStyle}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                    Confirm New Password
                  </label>
                  <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                    placeholder="Repeat your new password" required style={inputStyle}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>

                {/* Password rules */}
                <div style={{ padding: "12px 14px", background: "var(--surface-sunken)", borderRadius: 10 }}>
                  <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)",
                    margin: "0 0 8px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Password Requirements
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                    {RULES.map(r => {
                      const ok = r.re.test(next);
                      return (
                        <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 7 }}>
                          <span style={{ fontSize: 13, color: ok ? "var(--success-text)" : "var(--text-tertiary)" }}>
                            {ok ? "✓" : "○"}
                          </span>
                          <span style={{ fontSize: 12, color: ok ? "var(--success-text)" : "var(--text-secondary)" }}>
                            {r.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button type="submit" disabled={loading}
                  style={{ height: 44, borderRadius: 11, border: "none", background: "var(--brand)",
                    color: "white", fontWeight: 600, fontSize: 14,
                    cursor: loading ? "not-allowed" : "pointer",
                    opacity: loading ? 0.7 : 1, fontFamily: "inherit", transition: "opacity 0.15s" }}>
                  {loading ? "Changing password…" : "Change Password"}
                </button>
              </form>
            </>
          )}

          <button onClick={logout}
            style={{ width: "100%", marginTop: 16, padding: "10px 0", border: "none", background: "none",
              color: "var(--text-tertiary)", fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>
            Sign out instead
          </button>
        </div>
      </div>
    </div>
  );
}
