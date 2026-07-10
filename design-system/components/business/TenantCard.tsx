/** TenantCard — tenant summary with health score and billing mode. */
import React from "react";
import { Avatar } from "../ui/Avatar";
import { HealthScoreMeter } from "./HealthScoreMeter";
import { Badge } from "../ui/Badge";

export interface TenantData {
  id: string; name: string; vertical: string; city: string;
  healthScore: number; billingMode: string; walletBalance?: number;
  planType: string; isActive: boolean;
}

export function TenantCard({ tenant, onClick }:{ tenant:TenantData; onClick?:()=>void }) {
  const modeColor = tenant.billingMode === "credit_commission" ? "info"
                  : tenant.billingMode === "subscription_leads" ? "success" : "default";
  return (
    <div onClick={onClick} style={{
      background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"14px", padding:"18px 20px", cursor:onClick?"pointer":undefined,
      boxShadow:"var(--shadow-sm)", transition:"all 0.15s ease",
      display:"flex", flexDirection:"column", gap:"14px",
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow-md)";
      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--color-border-strong)";
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow-sm)";
      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--color-border)";
    }}>
      <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
        <Avatar name={tenant.name} size={40}/>
        <div style={{ flex:1, minWidth:0 }}>
          <p style={{ fontSize:"14px", fontWeight:600, color:"var(--color-text-primary)", margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
            {tenant.name}
          </p>
          <p style={{ fontSize:"12px", color:"var(--color-text-tertiary)", margin:"2px 0 0" }}>
            {tenant.vertical} · {tenant.city}
          </p>
        </div>
        <Badge variant={tenant.isActive ? "success" : "muted"} size="sm">
          {tenant.isActive ? "Active" : "Inactive"}
        </Badge>
      </div>
      <HealthScoreMeter score={tenant.healthScore}/>
      <div style={{ display:"flex", gap:"8px", flexWrap:"wrap" }}>
        <Badge variant={modeColor as any} size="sm">{tenant.billingMode.replace(/_/g," ")}</Badge>
        <Badge variant="muted" size="sm">{tenant.planType}</Badge>
      </div>
    </div>
  );
}
