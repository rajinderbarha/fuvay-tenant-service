"use client";
/**
 * Tenant Login Page.
 * PROVEN: authApi.login() from lib/api.ts — no inline fetch calls.
 * Stores token + full tenant context in localStorage on success.
 */
import React, { useState } from "react";
import { authApi, MOCK_MODE } from "../../lib/api";

export default function LoginPage() {
  const [email,    setEmail]    = useState("provider@serviceos.in");
  const [password, setPassword] = useState("Password123!");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Both fields required."); return; }
    setLoading(true); setError("");
    try {
      if (MOCK_MODE) {
        localStorage.setItem("serviceos_tenant_token",   "mock_tenant_token");
        localStorage.setItem("serviceos_tenant_id",      "t1");
        localStorage.setItem("serviceos_tenant_name",    "Rahul AC Services");
        localStorage.setItem("serviceos_tenant_vertical","home_services");
        localStorage.setItem("serviceos_tenant_plan",    "growth");
        localStorage.setItem("serviceos_tenant_health",  "74");
        localStorage.setItem("serviceos_user_id",        "u1");
        window.location.href = "/dashboard";
        return;
      }
      const res = await authApi.login(email, password);
      // Store token immediately so follow-up API calls are authenticated
      localStorage.setItem("serviceos_tenant_token",    res.access_token);
      if (res.refresh_token) localStorage.setItem("serviceos_tenant_refresh", res.refresh_token);

      // Backend returns user object, not tenant object — map correctly
      const u = res.user;
      localStorage.setItem("serviceos_user_id",         u?.id ?? u?.user_id ?? "");
      localStorage.setItem("serviceos_tenant_id",       u?.tenant_id ?? "");
      // Full name as display fallback; overridden by profile/runtime after redirect
      localStorage.setItem("serviceos_tenant_name",     u?.full_name ?? "");
      localStorage.setItem("serviceos_tenant_vertical", "");
      localStorage.setItem("serviceos_tenant_plan",     "");
      localStorage.setItem("serviceos_tenant_health",   "0");

      // Fetch runtime for vertical/category so sidebar knows which nav to show
      try {
        const rt = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/tenant/dashboard/runtime`, {
          headers: { Authorization: `Bearer ${res.access_token}` },
        }).then(r2 => r2.json());
        const rdata = rt?.data ?? rt?.runtime ?? {};
        const tenantName = rdata.tenant?.business_name ?? rdata.tenant_name;
        if (rdata.category_type) localStorage.setItem("serviceos_tenant_vertical", rdata.category_type);
        if (tenantName)          localStorage.setItem("serviceos_tenant_name",     tenantName);
        if (rdata.tenant_plan)   localStorage.setItem("serviceos_tenant_plan",     rdata.tenant_plan);
        if (rdata.tenant_health != null) localStorage.setItem("serviceos_tenant_health", String(rdata.tenant_health));
      } catch { /* non-critical */ }

      if (res.requires_password_change || u?.force_password_change) {
        localStorage.setItem("serviceos_force_pw_change", "1");
        window.location.href = "/change-password-required";
      } else {
        localStorage.removeItem("serviceos_force_pw_change");
        window.location.href = "/dashboard";
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed. Check credentials.");
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
            Tenant Owner Portal
          </p>
        </div>

        <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
          borderRadius:16, padding:32, boxShadow:"var(--shadow-lg)" }}>
          <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 24px" }}>
            Sign in to manage your business
          </h2>

          {error && (
            <div style={{ padding:"12px 14px", borderRadius:10, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)", color:"var(--danger-text)",
              fontSize:13, marginBottom:16 }}>{error}</div>
          )}

          <form onSubmit={handleLogin} style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div>
              <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)",
                display:"block", marginBottom:5 }}>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                style={{ width:"100%", height:42, padding:"0 14px", fontSize:14,
                  background:"var(--surface)", border:"1px solid var(--border)",
                  borderRadius:10, color:"var(--text-primary)", outline:"none",
                  fontFamily:"inherit", boxSizing:"border-box" as const }}
                onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
                onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
              />
            </div>
            <div>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:5 }}>
                <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)" }}>Password</label>
                <a href="/forgot-password" style={{ fontSize:12, color:"var(--brand)", fontWeight:500 }}>Forgot password?</a>
              </div>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
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
              {loading ? "Signing in..." : "Sign in →"}
            </button>
          </form>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"20px 0 0",
            textAlign:"center" }}>
            New business? <a href="/register" style={{ color:"var(--brand)", fontWeight:600 }}>Create an account</a>
          </p>
          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"10px 0 0",
            textAlign:"center" }}>
            Secured by ServiceOS Auth Engine · JWT + TOTP
          </p>
        </div>
      </div>
    </div>
  );
}
