"use client";
import React, { useState } from "react";
export type LifecycleAction = "activate"|"suspend"|"terminate"|"onboard_step"|"change_plan"|"change_billing_mode";
export interface TenantLifecycleActionsProps {
  tenantId:string; currentStatus:string; planType:string; billingMode:string; onboardingStep:number;
  onAction?: (action:LifecycleAction, payload?:Record<string,unknown>)=>void; loading?:LifecycleAction;
}
export function TenantLifecycleActions({ tenantId, currentStatus, planType, billingMode, onboardingStep, onAction, loading }: TenantLifecycleActionsProps) {
  const [confirm, setConfirm] = useState<LifecycleAction|null>(null);
  const active    = currentStatus === "active";
  const suspended = currentStatus === "suspended";
  const actions = [
    { id:"activate"   as LifecycleAction, label:"Activate",   variant:"success" as const, show: !active    },
    { id:"suspend"    as LifecycleAction, label:"Suspend",    variant:"danger"  as const, show: active      },
    { id:"change_plan"as LifecycleAction, label:"Change Plan", variant:"default" as const, show: true       },
    { id:"onboard_step"as LifecycleAction, label:`Step ${onboardingStep}/8`, variant:"default" as const, show: onboardingStep < 8 },
  ].filter(a => a.show);
  const varStyle: Record<string,React.CSSProperties> = {
    success:{ background:"var(--color-success-bg)", color:"var(--color-success-text)", border:"1px solid var(--color-success-border)" },
    danger: { background:"var(--color-danger-bg)",  color:"var(--color-danger-text)",  border:"1px solid var(--color-danger-border)"  },
    default:{ background:"var(--color-surface-base)", color:"var(--color-text-secondary)", border:"1px solid var(--color-border)"      },
  };
  return (
    <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
      {actions.map(a => (
        <button key={a.id} disabled={loading===a.id}
          onClick={() => { if (a.id==="suspend"||a.id==="terminate") { if(confirm!==a.id){setConfirm(a.id);return;} setConfirm(null); } onAction?.(a.id); }}
          style={{ padding:"7px 14px", borderRadius:"var(--radius-md)", cursor: loading===a.id?"not-allowed":"pointer",
            fontSize:"var(--text-xs)", fontFamily:"var(--font-sans)", fontWeight:"var(--font-semibold)",
            opacity: loading===a.id?0.6:1, transition:"all 0.15s", ...varStyle[a.variant] }}>
          {loading===a.id?"…":confirm===a.id?`Confirm ${a.label}?`:a.label}
        </button>
      ))}
    </div>
  );
}
