/** Modal — dialog overlay. */
import React, { useEffect } from "react";

export function Modal({ open, onClose, title, children, size="md" }:{
  open:boolean; onClose:()=>void; title?:string;
  children:React.ReactNode; size?:"sm"|"md"|"lg"|"xl";
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (e:KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;
  const widths = { sm:400, md:560, lg:720, xl:900 };
  return (
    <div style={{
      position:"fixed", inset:0, zIndex:300, display:"flex",
      alignItems:"center", justifyContent:"center",
      background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)",
      animation:"fadeIn 0.15s ease",
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        width:"100%", maxWidth: widths[size], maxHeight:"90vh", overflow:"auto",
        background:"var(--color-surface-overlay)",
        borderRadius:"18px", boxShadow:"var(--shadow-xl)",
        border:"1px solid var(--color-border)",
        animation:"slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)",
      }}>
        {title && (
          <div style={{
            display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"20px 24px", borderBottom:"1px solid var(--color-border)",
          }}>
            <h2 style={{ fontSize:"16px", fontWeight:600, color:"var(--color-text-primary)", margin:0 }}>{title}</h2>
            <button onClick={onClose} style={{
              background:"none", border:"none", cursor:"pointer", padding:"4px",
              color:"var(--color-text-tertiary)", borderRadius:"8px",
              display:"flex", alignItems:"center",
            }}>✕</button>
          </div>
        )}
        <div style={{ padding:"24px" }}>{children}</div>
      </div>
    </div>
  );
}
