"use client";
import React from "react";
export interface PermissionEntry { action:string; description?:string; }
export interface PermissionMatrixProps { permissions:PermissionEntry[]; roles:string[]; grants:Record<string,string[]>; onToggle?:(role:string,action:string,granted:boolean)=>void; }
export function PermissionMatrix({ permissions, roles, grants, onToggle }: PermissionMatrixProps) {
  return (
    <div style={{ overflowX:"auto" }}>
      <table style={{ width:"100%", borderCollapse:"collapse",
        background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
        borderRadius:"var(--radius-lg)", overflow:"hidden" }}>
        <thead>
          <tr style={{ background:"var(--color-surface-sunken)", borderBottom:"1px solid var(--color-border)" }}>
            <th style={{ padding:"10px 16px", textAlign:"left", fontSize:"var(--text-xs)",
              fontWeight:"var(--font-bold)", color:"var(--color-text-tertiary)",
              textTransform:"uppercase", letterSpacing:"0.06em" }}>Permission</th>
            {roles.map(r => (
              <th key={r} style={{ padding:"10px 12px", textAlign:"center", fontSize:"var(--text-xs)",
                fontWeight:"var(--font-bold)", color:"var(--color-text-tertiary)",
                textTransform:"uppercase", letterSpacing:"0.06em", whiteSpace:"nowrap" }}>
                {r.replace(/_/g," ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {permissions.map((p, i) => (
            <tr key={p.action} style={{ borderBottom: i<permissions.length-1?"1px solid var(--color-border)":"none" }}>
              <td style={{ padding:"10px 16px" }}>
                <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                  color:"var(--color-text-primary)", margin:0, fontFamily:"var(--font-mono)" }}>
                  {p.action}
                </p>
                {p.description && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)", margin:0 }}>
                  {p.description}
                </p>}
              </td>
              {roles.map(r => {
                const granted = grants[r]?.includes(p.action) ?? false;
                return (
                  <td key={r} style={{ padding:"10px 12px", textAlign:"center" }}>
                    <button onClick={() => onToggle?.(r, p.action, !granted)} title={granted?"Revoke":"Grant"}
                      style={{ width:22, height:22, borderRadius:"var(--radius-sm)",
                        border:`1px solid ${granted?"var(--color-success-border)":"var(--color-border)"}`,
                        background: granted?"var(--color-success-bg)":"transparent",
                        color: granted?"var(--color-success-text)":"var(--color-text-tertiary)",
                        cursor: onToggle?"pointer":"default",
                        display:"inline-flex", alignItems:"center", justifyContent:"center",
                        fontSize:12, fontWeight:"var(--font-bold)", transition:"all 0.12s" }}>
                      {granted?"✓":"–"}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
