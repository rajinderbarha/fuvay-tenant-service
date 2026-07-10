/** Switch — toggle control. */
import React from "react";

export function Switch({ checked, onChange, label, size="md" }:{
  checked: boolean; onChange: (v:boolean)=>void; label?:string; size?:"sm"|"md";
}) {
  const w = size === "sm" ? 34 : 42;
  const h = size === "sm" ? 20 : 24;
  const knob = h - 4;
  return (
    <label style={{ display:"flex", alignItems:"center", gap:"10px", cursor:"pointer", userSelect:"none" }}>
      <div
        role="switch" aria-checked={checked} tabIndex={0}
        onClick={() => onChange(!checked)}
        onKeyDown={e => e.key === " " && onChange(!checked)}
        style={{
          width: w, height: h, borderRadius: "9999px", position: "relative",
          background: checked ? "var(--color-accent)" : "var(--color-border-strong)",
          transition: "background 0.2s ease", cursor: "pointer",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <span style={{
          position: "absolute", top: 2, left: checked ? w - knob - 2 : 2,
          width: knob, height: knob, borderRadius: "9999px",
          background: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
          transition: "left 0.2s cubic-bezier(0.34,1.56,0.64,1)",
        }}/>
      </div>
      {label && <span style={{ fontSize:"14px", color:"var(--color-text-primary)" }}>{label}</span>}
    </label>
  );
}
