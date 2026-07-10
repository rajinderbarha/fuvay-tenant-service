"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { customerLogin } from "../../lib/api/auth";
import ErrorBanner from "../../components/ErrorBanner";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="co-container" style={{ paddingTop: 64 }} />}>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/customer/home-services";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      await customerLogin(email, password);
      router.push(next);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="co-container" style={{ paddingTop: 64 }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div style={{ width: 56, height: 56, borderRadius: 18, background: "var(--primary-gradient)", margin: "0 auto 16px", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "var(--shadow-md)" }}>
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 22 }}>S</span>
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Welcome back</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Sign in to book a home service</p>
      </div>
      <form onSubmit={handleSubmit} className="co-card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)}
          style={{ padding: 14, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 16 }} />
        <input type="password" required placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)}
          style={{ padding: 14, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 16 }} />
        <ErrorBanner error={error} />
        <button type="submit" disabled={loading} className="co-btn-primary">{loading ? "Signing in..." : "Sign In"}</button>
      </form>
    </div>
  );
}
