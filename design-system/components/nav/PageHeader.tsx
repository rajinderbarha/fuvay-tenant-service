"use client";
import React from "react";
export interface Breadcrumb { label: string; href?: string; }
export interface PageHeaderProps {
  title: string; subtitle?: string; actions?: React.ReactNode;
  breadcrumbs?: Breadcrumb[]; badge?: React.ReactNode; meta?: React.ReactNode;
}
export function PageHeader({ title, subtitle, actions, breadcrumbs, badge, meta }: PageHeaderProps) {
  return (
    <div style={{ marginBottom:24 }}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="breadcrumb" style={{ display:"flex", alignItems:"center", gap:6,
          marginBottom:10, fontSize:"var(--text-sm)", color:"var(--color-text-tertiary)" }}>
          {breadcrumbs.map((b, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span style={{ opacity:0.5 }}>›</span>}
              {b.href
                ? <a href={b.href} style={{ color:"var(--color-text-link)", textDecoration:"none" }}
                    onMouseEnter={e=>(e.target as HTMLElement).style.textDecoration="underline"}
                    onMouseLeave={e=>(e.target as HTMLElement).style.textDecoration="none"}>{b.label}</a>
                : <span style={{ color:"var(--color-text-secondary)", fontWeight:"var(--font-medium)" }}>{b.label}</span>
              }
            </React.Fragment>
          ))}
        </nav>
      )}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between",
        gap:16, flexWrap:"wrap" }}>
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:10, flexWrap:"wrap" }}>
            <h1 style={{ fontSize:"var(--text-3xl)", fontWeight:"var(--font-bold)",
              color:"var(--color-text-primary)", margin:0, letterSpacing:"-0.02em" }}>{title}</h1>
            {badge}
          </div>
          {subtitle && <p style={{ fontSize:"var(--text-base)", color:"var(--color-text-secondary)",
            margin:"5px 0 0", lineHeight:1.5 }}>{subtitle}</p>}
          {meta && <div style={{ marginTop:8 }}>{meta}</div>}
        </div>
        {actions && (
          <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>{actions}</div>
        )}
      </div>
    </div>
  );
}
