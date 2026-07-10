"use client";
import React from "react";
export interface SelectOption { value: string; label: string; disabled?: boolean; }
export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>,"children"> {
  label?: string; error?: string; hint?: string; options: SelectOption[];
  placeholder?: string; icon?: React.ReactNode;
}
export function Select({ label, error, hint, options, placeholder, icon, id, style, ...props }: SelectProps) {
  const uid = id || label?.toLowerCase().replace(/\s+/g,"-");
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
      {label && <label htmlFor={uid} style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
        color:"var(--color-text-secondary)" }}>{label}</label>}
      <div style={{ position:"relative" }}>
        {icon && <span style={{ position:"absolute", left:11, top:"50%", transform:"translateY(-50%)",
          color:"var(--color-text-tertiary)", pointerEvents:"none", zIndex:1 }}>{icon}</span>}
        <select id={uid} {...props}
          style={{ width:"100%", height:38, padding:`0 36px 0 ${icon ? "36px" : "12px"}`,
            fontSize:"var(--text-base)", fontFamily:"var(--font-sans)",
            background:"var(--input-bg)",
            border:`1px solid ${error ? "var(--color-danger)" : "var(--input-border)"}`,
            borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
            outline:"none", cursor:"pointer", appearance:"none",
            backgroundImage:`url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
            backgroundRepeat:"no-repeat", backgroundPosition:"right 10px center",
            boxSizing:"border-box" as const, ...style }}>
          {placeholder && <option value="">{placeholder}</option>}
          {options.map(o => <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>)}
        </select>
      </div>
      {error && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:0 }}>{error}</p>}
      {hint && !error && <p style={{ fontSize:"var(--text-sm)", color:"var(--color-text-tertiary)", margin:0 }}>{hint}</p>}
    </div>
  );
}
