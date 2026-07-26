"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "../../../lib/api";
import { authTimeline } from "../../../lib/authTimeline";

export default function StaffLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [requestId, setRequestId] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Both fields are required."); return; }
    setLoading(true); setError(""); setRequestId(null);
    authTimeline("login.submit");
    try {
      const res = await authApi.login(email, password);
      authTimeline("login.response_received");
      const u = res.user;
      if (u?.role !== "technician" && u?.role !== "staff") {
        setError("This login is for staff/technician accounts only. Please use the owner portal.");
        setLoading(false);
        return;
      }
      localStorage.setItem("serviceos_tenant_token", res.access_token);
      if (res.refresh_token) localStorage.setItem("serviceos_tenant_refresh", res.refresh_token);
      localStorage.setItem("serviceos_user_id", u?.id ?? u?.user_id ?? "");
      localStorage.setItem("serviceos_tenant_id", u?.tenant_id ?? "");
      localStorage.setItem("serviceos_tenant_name", res.tenant?.name ?? "");
      localStorage.setItem("serviceos_user_role", u?.role ?? "");
      authTimeline("login.session_persisted");
      // FINAL-L5-01D fix: window.location.href triggered a full page reload,
      // which is slower than necessary and was not reliably trackable by
      // browser-automation navigation waits in this dev environment. Next.js
      // router.push() is a client-side SPA transition -- faster, no white
      // flash, and deterministic. See
      // FINAL_L5_01D_TECHNICIAN_REDIRECT_ROOT_CAUSE_REPORT.md.
      router.push("/staff/dashboard");
      authTimeline("login.router_push_called");
    } catch (e: unknown) {
      const err = e as { message?: string; requestId?: string };
      authTimeline("login.error", err?.message);
      setError(err?.message || "Login failed. Check credentials.");
      setRequestId(err?.requestId ?? null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg)", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: "var(--brand)",
            display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px" }}>
            <span style={{ color: "white", fontWeight: 800, fontSize: 20 }}>T</span>
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>Technician App</h1>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "4px 0 0" }}>Staff / Technician sign-in</p>
        </div>

        <form onSubmit={handleLogin} style={{ background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 14, padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
          {error && (
            <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--danger-bg, #fef2f2)",
              border: "1px solid var(--danger-border, #fecaca)", fontSize: 12, color: "var(--danger-text, #b91c1c)" }}>
              {error}
              {requestId && <div style={{ marginTop: 4, opacity: 0.8 }}>Request ID: {requestId}</div>}
            </div>
          )}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 6 }}>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="technician@example.com" required
              style={{ width: "100%", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--card-bg)", color: "var(--text)", fontSize: 13 }}/>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 6 }}>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required
              style={{ width: "100%", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--card-bg)", color: "var(--text)", fontSize: 13 }}/>
          </div>
          <button type="submit" disabled={loading} style={{
            padding: "10px 16px", borderRadius: 8, border: "none", background: "var(--brand)",
            color: "white", fontWeight: 600, fontSize: 13, cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
          <Link href="/forgot-password" style={{ fontSize: 12, color: "var(--text-tertiary)", textAlign: "center" }}>
            Forgot password?
          </Link>
        </form>
      </div>
    </div>
  );
}
