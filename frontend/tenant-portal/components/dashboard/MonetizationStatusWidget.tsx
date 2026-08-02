"use client";
import React, { useCallback } from "react";
import { ShieldCheck, AlertTriangle, CreditCard, Calendar, Lock } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import { providerMonetizationApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

const MODEL_LABEL: Record<string, string> = {
  credit_wallet_commission: "Credit Wallet + Commission",
  subscription: "Subscription",
  freemium: "Freemium",
  fixed_billing: "Fixed Billing",
};

const SUB_STATUS_COLOR: Record<string, string> = {
  active: "var(--success)",
  trialing: "#2563eb",
  past_due: "var(--warning)",
  cancelled: "var(--danger)",
  none: "#64748b",
};

export function MonetizationStatusWidget() {
  const status = useApi(useCallback(() => providerMonetizationApi.getStatus(), []));
  const s = status.data;

  if (status.loading) {
    return (
      <Card>
        <div style={{ padding:"20px 24px", display:"flex", alignItems:"center", gap:12 }}>
          <div style={{ width:32, height:32, borderRadius:"50%", background:"var(--surface-sunken)", flexShrink:0 }}/>
          <div style={{ flex:1 }}>
            <div style={{ height:14, width:180, borderRadius:6, background:"var(--surface-sunken)", marginBottom:8 }}/>
            <div style={{ height:11, width:120, borderRadius:6, background:"var(--surface-sunken)" }}/>
          </div>
        </div>
      </Card>
    );
  }

  if (status.error || !s) {
    return null;
  }

  const isBookable = s.is_bookable;
  const isReady = s.is_monetization_ready;
  const isOverridden = s.override_is_bookable !== null;

  return (
    <Card>
      <div style={{ padding:"20px 24px" }}>
        {/* Header */}
        <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:16 }}>
          {isBookable ? (
            <ShieldCheck size={18} style={{ color:"var(--success)", flexShrink:0 }}/>
          ) : (
            <AlertTriangle size={18} style={{ color:"var(--warning)", flexShrink:0 }}/>
          )}
          <span style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>
            Monetization Status
          </span>
          <Badge variant={isBookable ? "success" : "warning"} size="sm">
            {isBookable ? "Active & Bookable" : "Not Bookable"}
          </Badge>
          {isOverridden && (
            <span style={{ display:"flex", alignItems:"center", gap:4, fontSize:11,
              color:"var(--warning)", fontWeight:600 }}>
              <Lock size={11}/> Admin Override
            </span>
          )}
        </div>

        {/* Status grid */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>

          {/* Monetization model */}
          {s.monetization_model && (
            <StatusCard
              label="Model"
              value={MODEL_LABEL[s.monetization_model] ?? s.monetization_model}
              icon={<CreditCard size={14}/>}
              accent="var(--accent)"
            />
          )}

          {/* Subscription model */}
          {s.monetization_model === "subscription" && (
            <StatusCard
              label="Subscription"
              value={s.subscription_status ?? "None"}
              icon={<Calendar size={14}/>}
              accent={SUB_STATUS_COLOR[s.subscription_status ?? "none"]}
              sub={s.subscription_expires_at
                ? `Expires ${new Date(s.subscription_expires_at).toLocaleDateString()}`
                : undefined}
            />
          )}

          {/* Credit wallet model */}
          {s.monetization_model === "credit_wallet_commission" && (
            <>
              <StatusCard
                label="Credit Balance"
                value={`₹${s.credit_balance.toFixed(2)}`}
                icon={<CreditCard size={14}/>}
                accent={s.credit_balance >= s.credit_minimum_required ? "var(--success)" : "var(--danger)"}
                sub={`Minimum required: ₹${s.credit_minimum_required.toFixed(2)}`}
              />
              <StatusCard
                label="Security Deposit"
                value={s.deposit_paid ? "Paid" : "Unpaid"}
                icon={<ShieldCheck size={14}/>}
                accent={s.deposit_paid ? "var(--success)" : "var(--danger)"}
              />
            </>
          )}

          {/* Readiness */}
          <StatusCard
            label="Monetization Ready"
            value={isReady ? "Yes" : "No"}
            icon={<ShieldCheck size={14}/>}
            accent={isReady ? "var(--success)" : "var(--warning)"}
          />
        </div>

        {/* Override notice */}
        {isOverridden && s.override_reason && (
          <div style={{ marginTop:14, padding:"10px 14px", borderRadius:8,
            background:"rgba(250,170,0,0.08)", border:"1px solid rgba(250,170,0,0.25)" }}>
            <p style={{ margin:0, fontSize:12, color:"#b45309", fontWeight:600 }}>
              Admin Override Active
            </p>
            <p style={{ margin:"3px 0 0", fontSize:12, color:"var(--text-secondary)" }}>
              {s.override_reason}
            </p>
          </div>
        )}

        {/* Last synced */}
        {s.last_synced_at && (
          <p style={{ margin:"14px 0 0", fontSize:11, color:"var(--text-tertiary)" }}>
            Last synced: {new Date(s.last_synced_at).toLocaleString()}
          </p>
        )}
      </div>
    </Card>
  );
}

function StatusCard({
  label, value, icon, accent, sub,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  accent: string;
  sub?: string;
}) {
  return (
    <div style={{ padding:"12px 14px", borderRadius:10, background:"var(--surface-sunken)",
      border:"1px solid var(--border)" }}>
      <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:6, color: accent }}>
        {icon}
        <span style={{ fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.05em" }}>
          {label}
        </span>
      </div>
      <p style={{ margin:0, fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>{value}</p>
      {sub && <p style={{ margin:"3px 0 0", fontSize:11, color:"var(--text-tertiary)" }}>{sub}</p>}
    </div>
  );
}
