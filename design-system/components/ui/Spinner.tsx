/** Spinner — loading indicator. */
import React from "react";

export function Spinner({ size = 20, color = "var(--color-accent)" }:{size?:number;color?:string}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         style={{ animation: "spin 0.7s linear infinite", display:"block" }}>
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" opacity="0.2"/>
      <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round"/>
    </svg>
  );
}
