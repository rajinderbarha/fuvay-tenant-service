"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { CheckCircle2, KeyRound } from "lucide-react";
import { providerTeamMembersApi, ServiceOSError } from "../../lib/api";

export default function ActivateTeamMemberPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!token.trim()) return setError("Enter the activation code from your invitation.");
    if (password !== confirmPassword) return setError("Passwords do not match.");
    setSubmitting(true);
    try {
      await providerTeamMembersApi.activateLogin(token.trim(), password);
      setComplete(true);
    } catch (caught) {
      setError(caught instanceof ServiceOSError ? caught.message : "We couldn't activate this account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "var(--bg-gradient)" }}>
      <section style={{ width: "100%", maxWidth: 440, padding: 28, borderRadius: 16, background: "var(--surface)", border: "1px solid var(--border)", boxShadow: "var(--shadow-lg)" }}>
        <div style={{ width: 44, height: 44, display: "grid", placeItems: "center", borderRadius: 12, background: "var(--brand-soft)", color: "var(--brand)", marginBottom: 18 }}>
          {complete ? <CheckCircle2 size={22}/> : <KeyRound size={22}/>}
        </div>
        <h1 style={{ margin: "0 0 8px", fontSize: 24, color: "var(--text-primary)" }}>
          {complete ? "Account activated" : "Activate your team account"}
        </h1>
        <p style={{ margin: "0 0 22px", fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)" }}>
          {complete ? "Your password is set. You can now sign in to Fuvay." : "Enter the one-time code from your invitation and choose your password."}
        </p>
        {complete ? (
          <Link href="/login" style={{ display: "block", padding: "11px 16px", borderRadius: 8, background: "var(--brand)", color: "var(--text-on-brand)", textAlign: "center", fontWeight: 700, textDecoration: "none" }}>Continue to sign in</Link>
        ) : (
          <form onSubmit={submit}>
            {error && <div role="alert" style={{ marginBottom: 14, padding: "10px 12px", borderRadius: 8, border: "1px solid var(--danger-border)", background: "var(--danger-bg)", color: "var(--danger-text)", fontSize: 13 }}>{error}</div>}
            <label htmlFor="activation-code" style={labelStyle}>Activation code</label>
            <input id="activation-code" value={token} onChange={event => setToken(event.target.value)} autoComplete="one-time-code" style={inputStyle}/>
            <label htmlFor="new-password" style={labelStyle}>New password</label>
            <input id="new-password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" style={inputStyle}/>
            <label htmlFor="confirm-password" style={labelStyle}>Confirm password</label>
            <input id="confirm-password" type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} autoComplete="new-password" style={inputStyle}/>
            <button type="submit" disabled={submitting} style={{ width: "100%", marginTop: 6, padding: "11px 16px", border: 0, borderRadius: 8, background: "var(--brand)", color: "var(--text-on-brand)", fontWeight: 700, cursor: submitting ? "wait" : "pointer", opacity: submitting ? 0.7 : 1 }}>
              {submitting ? "Activating…" : "Activate account"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}

const labelStyle = { display: "block", marginBottom: 6, fontSize: 13, fontWeight: 600, color: "var(--text-primary)" } as const;
const inputStyle = { width: "100%", height: 42, marginBottom: 15, padding: "0 12px", boxSizing: "border-box", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", font: "inherit" } as const;
