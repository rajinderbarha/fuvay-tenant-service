"use client";
import React, { useRef, useEffect } from "react";
export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>,"type"> {
  label?: string; description?: string; indeterminate?: boolean; error?: string;
}
export function Checkbox({ label, description, indeterminate, error, id, ...props }: CheckboxProps) {
  const ref = useRef<HTMLInputElement>(null);
  const uid = id || label?.toLowerCase().replace(/\s+/g,"-") || "cb";
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = !!indeterminate;
  }, [indeterminate]);
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
      <label htmlFor={uid} style={{ display:"flex", alignItems:"flex-start", gap:10,
        cursor: props.disabled ? "not-allowed" : "pointer", userSelect:"none",
        opacity: props.disabled ? 0.55 : 1 }}>
        <div style={{ position:"relative", flexShrink:0, marginTop:1 }}>
          <input ref={ref} type="checkbox" id={uid} {...props}
            style={{ position:"absolute", opacity:0, width:18, height:18, margin:0, cursor:"inherit" }}/>
          <div style={{ width:18, height:18, borderRadius:"var(--radius-sm)",
            border:`2px solid ${props.checked||indeterminate ? "var(--color-accent)" : "var(--color-border-strong)"}`,
            background: props.checked||indeterminate ? "var(--color-accent)" : "var(--input-bg)",
            display:"flex", alignItems:"center", justifyContent:"center",
            transition:"all 0.15s", pointerEvents:"none" }}>
            {(props.checked && !indeterminate) && (
              <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
            {indeterminate && (
              <svg width="10" height="2" viewBox="0 0 10 2" fill="none">
                <path d="M1 1H9" stroke="white" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            )}
          </div>
        </div>
        {(label || description) && (
          <div>
            {label && <span style={{ fontSize:"var(--text-base)", color:"var(--color-text-primary)",
              fontWeight:"var(--font-medium)" }}>{label}</span>}
            {description && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-tertiary)", margin:"2px 0 0" }}>
              {description}</p>}
          </div>
        )}
      </label>
      {error && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:0, paddingLeft:28 }}>
        {error}</p>}
    </div>
  );
}
