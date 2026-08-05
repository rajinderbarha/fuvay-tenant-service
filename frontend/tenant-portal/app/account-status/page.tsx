"use client";
/**
 * Restricted/rejected/multi-vertical landing page — reached only via the
 * backend-authoritative post-login destination projection (next_destination
 * of restricted_account / rejection_status / workspace_vertical_selector).
 * Shows real account context from /v1/auth/me, never a fabricated message.
 */
import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ShieldAlert, XCircle, Layers, LogOut } from "lucide-react";
import { authApi, getToken } from "../../lib/api";
import { T } from "../../lib/tenantAuthTheme";

const COPY: Record<string, { icon: React.ReactNode; title: string; body: string }> = {
  restricted_account: {
    icon: <ShieldAlert size={28} color={T.warning} />,
    title: "Access to this workspace is currently restricted",
    body: "Your business account has been suspended. Contact support for details on how to resolve this.",
  },
  rejection_status: {
    icon: <XCircle size={28} color={T.error} />,
    title: "This application was not approved",
    body: "Your business registration or vertical application was rejected. Contact support if you believe this is a mistake.",
  },
  workspace_vertical_selector: {
    icon: <Layers size={28} color={T.orange} />,
    title: "Choose a workspace",
    body: "Your account has more than one business vertical in progress. Vertical switching is managed from your workspace settings once you're signed in to any active vertical.",
  },
};

export default function AccountStatusPage() {
  return (
    <Suspense fallback={null}>
      <AccountStatusContent />
    </Suspense>
  );
}

function AccountStatusContent() {
  const router = useRouter();
  const params = useSearchParams();
  const reason = params.get("reason") || "restricted_account";
  const copy = COPY[reason] || COPY.restricted_account;

  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    authApi.me().then(u => setEmail(u.email)).catch(() => {});
  }, [router]);

  async function signOut() {
    try { await authApi.logout(); } catch { /* proceed regardless */ }
    localStorage.removeItem("serviceos_tenant_token");
    localStorage.removeItem("serviceos_tenant_refresh");
    router.replace("/login");
  }

  return (
    <div style={{ minHeight: "100vh", background: T.pageBg, color: T.textPrimary, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ maxWidth: 480, width: "100%", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 36, textAlign: "center" }}>
        <div style={{ width: 60, height: 60, borderRadius: "50%", background: T.surface2, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 18px" }}>
          {copy.icon}
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 10px" }}>{copy.title}</h1>
        <p style={{ fontSize: 14, color: T.textSecondary, margin: "0 0 8px", lineHeight: 1.6 }}>{copy.body}</p>
        {email && <p style={{ fontSize: 12, color: T.textMuted, margin: "0 0 24px" }}>Signed in as {email}</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <a href="mailto:support@serviceos.app" style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: 44, borderRadius: 10,
            background: T.orange, color: "#151617", fontWeight: 700, fontSize: 14, textDecoration: "none",
          }}>Contact support</a>
          <button onClick={signOut} style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: 44, borderRadius: 10,
            border: `1px solid ${T.border}`, background: "transparent", color: T.textPrimary, fontWeight: 600,
            fontSize: 14, cursor: "pointer",
          }}><LogOut size={16} /> Sign out</button>
        </div>
      </div>
    </div>
  );
}
