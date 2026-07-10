/** Toast — notification message. */
import React from "react";
import type { Toast as ToastType, ToastVariant } from "../../hooks/useToast";

const VARIANT_STYLE: Record<ToastVariant, React.CSSProperties> = {
  success: { borderLeft:"3px solid var(--color-success)", background:"var(--color-success-bg)" },
  warning: { borderLeft:"3px solid var(--color-warning)", background:"var(--color-warning-bg)" },
  danger:  { borderLeft:"3px solid var(--color-danger)",  background:"var(--color-danger-bg)"  },
  info:    { borderLeft:"3px solid var(--color-info)",    background:"var(--color-info-bg)"    },
  default: { borderLeft:"3px solid var(--color-border-strong)", background:"var(--color-surface-base)" },
};

export function Toaster({ toasts, onRemove }:{
  toasts: ToastType[]; onRemove:(id:string)=>void;
}) {
  return (
    <div style={{ position:"fixed", bottom:24, right:24, zIndex:400, display:"flex", flexDirection:"column", gap:"10px" }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          display:"flex", alignItems:"flex-start", gap:"12px",
          padding:"14px 18px", borderRadius:"12px", minWidth:280, maxWidth:380,
          boxShadow:"var(--shadow-lg)", border:"1px solid var(--color-border)",
          animation:"slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)",
          ...VARIANT_STYLE[t.variant],
        }}>
          <div style={{ flex:1 }}>
            <p style={{ fontSize:"13px", fontWeight:600, color:"var(--color-text-primary)", margin:0 }}>{t.title}</p>
            {t.description && <p style={{ fontSize:"12px", color:"var(--color-text-secondary)", margin:"3px 0 0" }}>{t.description}</p>}
          </div>
          <button onClick={() => onRemove(t.id)} style={{
            background:"none", border:"none", cursor:"pointer",
            color:"var(--color-text-tertiary)", fontSize:"14px", padding:"0", lineHeight:1,
          }}>✕</button>
        </div>
      ))}
    </div>
  );
}
