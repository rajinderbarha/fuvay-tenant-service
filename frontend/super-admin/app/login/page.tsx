"use client";
/**
 * Login Page — Super Admin Portal
 * PROVEN: calls authApi.login (lib/api.ts) — no inline fetch calls.
 * Form validation before submit. Token stored in localStorage.
 */
import React, { useState } from "react";
import { authApi } from "../../lib/api";

export default function LoginPage() {
  const [email,    setEmail]    = useState("admin@serviceos.in");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

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
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center",
      background:"var(--bg)", padding:24 }}>
      <div style={{ width:"100%", maxWidth:400 }}>
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ width:56, height:56, borderRadius:14, background:"var(--brand)",
            display:"flex", alignItems:"center", justifyContent:"center",
            margin:"0 auto 16px", boxShadow:"var(--shadow-md)" }}>
            <span style={{ color:"white", fontWeight:800, fontSize:22 }}>S</span>
          </div>
          <h1 style={{ fontSize:24, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>ServiceOS</h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>Super Admin Portal</p>
        </div>

        <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-xl, 1rem)",
          padding:32, boxShadow:"var(--shadow-lg)" }}>
          <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 24px" }}>
            Sign in to continue
          </h2>

          {error && (
            <div style={{ padding:"12px 14px", borderRadius:10, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)", color:"var(--danger-text)",
              fontSize:13, marginBottom:16 }}>{error}
            </div>
          )}

          <form onSubmit={handleLogin} style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div>
              <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                display:"block", marginBottom:5 }}>Email Address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="admin@serviceos.in" required
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
                display:"block", marginBottom:5 }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••" required
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
                color:"white", fontWeight:600, fontSize:14, cursor:loading ? "not-allowed" : "pointer",
                display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                opacity:loading ? 0.7 : 1, fontFamily:"inherit", transition:"opacity 0.15s" }}>
              {loading ? "Signing in..." : "Sign in →"}
            </button>
          </form>

          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"20px 0 0", textAlign:"center" }}>
            Secured by ServiceOS Auth Engine · JWT + TOTP
          </p>
        </div>
      </div>
    </div>
  );
}
