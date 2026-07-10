/** PageContainer — responsive page wrapper. */
import React from "react";

export function PageContainer({ children, title, subtitle, actions, maxWidth=1400 }:{
  children:React.ReactNode; title?:string; subtitle?:string;
  actions?:React.ReactNode; maxWidth?:number;
}) {
  return (
    <main style={{ flex:1, padding:"28px 32px", overflowY:"auto", minHeight:0 }}>
      <div style={{ maxWidth, margin:"0 auto" }}>
        {(title||actions) && (
          <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:"24px", gap:"16px", flexWrap:"wrap" }}>
            <div>
              {title && <h1 style={{ fontSize:"22px", fontWeight:700, color:"var(--color-text-primary)", margin:0 }}>{title}</h1>}
              {subtitle && <p style={{ fontSize:"14px", color:"var(--color-text-secondary)", margin:"4px 0 0" }}>{subtitle}</p>}
            </div>
            {actions && <div style={{ display:"flex", gap:"10px", flexWrap:"wrap" }}>{actions}</div>}
          </div>
        )}
        {children}
      </div>
    </main>
  );
}
