"use client";
/**
 * Forgot Password — Super Admin Portal
 *   1. Enter email -> request OTP (authApi.requestPasswordReset)
 *   2. Enter OTP + new password -> confirm (authApi.confirmPasswordReset)
 * Same generic /v1/auth/password/reset/* endpoints used by every portal.
 */
import React, { useState } from "react";
import Link from "next/link";
import { authApi } from "../../lib/api";

type Step = "email" | "reset" | "done";

export default function ForgotPasswordPage() {
  const [step,     setStep]     = useState<Step>("email");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const [email,       setEmail]       = useState("");
  const [otp,          setOtp]        = useState("");
  const [newPassword,  setNewPassword]  = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  async function handleRequestReset(e: React.FormEvent) {
    e.preventDefault();
    if (!email) { setError("Email is required."); return; }
    setError(""); setLoading(true);
    try {
      await authApi.requestPasswordReset(email);
      setStep("reset");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not request password reset. Try again.");
    } finally { setLoading(false); }
  }

  async function handleConfirmReset(e: React.FormEvent) {
    e.preventDefault();
    if (!otp || otp.trim().length < 4) { setError("Enter the OTP sent to your email."); return; }
    if (newPassword.length < 8) { setError("New password must be at least 8 characters."); return; }
    if (newPassword !== confirmPassword) { setError("Passwords do not match."); return; }
    setError(""); setLoading(true);
    try {
      await authApi.confirmPasswordReset(email, otp.trim(), newPassword);
      setStep("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not reset password. Check your OTP and try again.");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center",
      justifyContent:"center", background:"var(--bg)", padding:24 }}>
      <div style={{ width:"100%", maxWidth:420 }}>
        {/* Logo */}
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ width:56, height:56, borderRadius:14, background:"var(--brand)",
            display:"flex", alignItems:"center", justifyContent:"center",
            margin:"0 auto 16px", boxShadow:"var(--shadow-md)" }}>
            <span style={{ color:"white", fontWeight:800, fontSize:22 }}>S</span>
          </div>
          <h1 style={{ fontSize:24, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
            ServiceOS
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Reset your admin password
          </p>
        </div>

        <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
          borderRadius:"var(--radius-xl, 1rem)", padding:32, boxShadow:"var(--shadow-lg)" }}>

          {error && (
            <div style={{ padding:"12px 14px", borderRadius:10, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)", color:"var(--danger-text)",
              fontSize:13, marginBottom:16 }}>{error}</div>
          )}

          {/* ── Step 1: Email ── */}
          {step === "email" && (
            <>
              <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 8px" }}>
                Forgot your password?
              </h2>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 24px", lineHeight:1.5 }}>
                Enter the email on your admin account and we&apos;ll send you a one-time code to reset your password.
              </p>
              <form onSubmit={handleRequestReset} style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <div>
                  <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                    display:"block", marginBottom:5 }}>Email</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                    placeholder="you@serviceos.in"
                    style={{ width:"100%", height:42, padding:"0 14px", fontSize:14,
                      background:"var(--surface)", border:"1px solid var(--border)",
                      borderRadius:10, color:"var(--text-primary)", outline:"none",
                      fontFamily:"inherit", boxSizing:"border-box" as const }}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>
                <button type="submit" disabled={loading}
                  style={{ height:44, borderRadius:11, border:"none", background:"var(--brand)",
                    color:"white", fontWeight:600, fontSize:14,
                    cursor:loading?"not-allowed":"pointer",
                    opacity:loading?0.7:1, fontFamily:"inherit", transition:"opacity 0.15s" }}>
                  {loading ? "Sending OTP..." : "Send reset code →"}
                </button>
              </form>
            </>
          )}

          {/* ── Step 2: OTP + new password ── */}
          {step === "reset" && (
            <>
              <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 8px" }}>
                Enter your reset code
              </h2>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 18px", lineHeight:1.5 }}>
                If an admin account exists for <strong style={{ color:"var(--text-primary)" }}>{email}</strong>,
                a 6-digit code has been sent. Enter it below with your new password.
              </p>

              <form onSubmit={handleConfirmReset} style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <div>
                  <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                    display:"block", marginBottom:5 }}>Reset code (OTP)</label>
                  <input type="text" inputMode="numeric" maxLength={6}
                    value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, ""))} required
                    placeholder="123456"
                    style={{ width:"100%", height:42, padding:"0 14px", fontSize:16, letterSpacing:"0.3em",
                      textAlign:"center", background:"var(--surface)", border:"1px solid var(--border)",
                      borderRadius:10, color:"var(--text-primary)", outline:"none",
                      fontFamily:"inherit", boxSizing:"border-box" as const }}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>
                <div>
                  <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                    display:"block", marginBottom:5 }}>New password</label>
                  <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required
                    placeholder="At least 8 characters"
                    style={{ width:"100%", height:42, padding:"0 14px", fontSize:14,
                      background:"var(--surface)", border:"1px solid var(--border)",
                      borderRadius:10, color:"var(--text-primary)", outline:"none",
                      fontFamily:"inherit", boxSizing:"border-box" as const }}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>
                <div>
                  <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                    display:"block", marginBottom:5 }}>Confirm new password</label>
                  <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required
                    placeholder="Re-enter new password"
                    style={{ width:"100%", height:42, padding:"0 14px", fontSize:14,
                      background:"var(--surface)", border:"1px solid var(--border)",
                      borderRadius:10, color:"var(--text-primary)", outline:"none",
                      fontFamily:"inherit", boxSizing:"border-box" as const }}
                    onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                    onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
                  />
                </div>
                <button type="submit" disabled={loading}
                  style={{ height:44, borderRadius:11, border:"none", background:"var(--brand)",
                    color:"white", fontWeight:600, fontSize:14,
                    cursor:loading?"not-allowed":"pointer",
                    opacity:loading?0.7:1, fontFamily:"inherit", transition:"opacity 0.15s" }}>
                  {loading ? "Resetting..." : "Reset password →"}
                </button>
                <button type="button" onClick={() => { setStep("email"); setOtp(""); setError(""); }}
                  style={{ height:38, borderRadius:11, border:"1px solid var(--border)", background:"transparent",
                    color:"var(--text-secondary)", fontWeight:500, fontSize:13,
                    cursor:"pointer", fontFamily:"inherit" }}>
                  ← Back / resend code
                </button>
              </form>
            </>
          )}

          {/* ── Step 3: Done ── */}
          {step === "done" && (
            <>
              <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 8px" }}>
                Password reset!
              </h2>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 24px", lineHeight:1.5 }}>
                Your password has been changed. You can now log in with your new password.
              </p>
              <Link href="/login" style={{ display:"block", textAlign:"center", height:44, lineHeight:"44px",
                borderRadius:11, background:"var(--brand)", color:"white", fontWeight:600, fontSize:14,
                textDecoration:"none" }}>
                Go to login →
              </Link>
            </>
          )}

          {step !== "done" && (
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"20px 0 0", textAlign:"center" }}>
              Remembered your password? <Link href="/login" style={{ color:"var(--brand)", fontWeight:600 }}>Sign in</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
