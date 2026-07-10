"use client";
import React from "react";
import { ROLE_MAP, type RoleKey } from "../../tokens/tokens";
export interface RoleBadgeProps { role: string; size?: "sm"|"md"; }
export function RoleBadge({ role, size="md" }: RoleBadgeProps) {
  const map = ROLE_MAP[role as RoleKey] ?? { cssClass:"role--api_key", label:role, priority:99 };
  return (
    <span className={map.cssClass}
      style={{ display:"inline-flex", alignItems:"center", gap:5,
        borderRadius:"var(--radius-full)", fontWeight:700,
        fontSize: size==="sm" ? "var(--text-xs)" : "var(--text-xs)",
        padding: size==="sm" ? "2px 7px" : "3px 9px",
        background:"var(--role-bg)", color:"var(--role-text)",
        border:"1px solid var(--role-border)", whiteSpace:"nowrap" }}>
      {map.label}
    </span>
  );
}
