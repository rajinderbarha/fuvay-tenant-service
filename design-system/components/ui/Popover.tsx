"use client";
import React, { useState, useRef, useEffect } from "react";
export interface PopoverProps { trigger: React.ReactElement; content: React.ReactNode; side?: "bottom"|"top"|"left"|"right"; }
export function Popover({ trigger, content, side = "bottom" }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function handle(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);
  const offset = side === "bottom" ? "calc(100% + 6px)" : side === "top" ? "auto" : "50%";
  const bottom  = side === "top" ? "calc(100% + 6px)" : "auto";
  return (
    <div ref={ref} style={{ position:"relative", display:"inline-flex" }}>
      {React.cloneElement(trigger, { onClick: () => setOpen(!open) })}
      {open && (
        <div role="dialog" style={{ position:"absolute", top: side==="bottom"?offset:"auto",
          bottom: side==="top"?bottom:"auto",
          left: side==="left"?"auto":side==="right"?"calc(100% + 6px)":0,
          right: side==="left"?"calc(100% + 6px)":"auto",
          minWidth:200, background:"var(--color-surface-elevated)",
          border:"1px solid var(--color-border)", borderRadius:"var(--radius-lg)",
          boxShadow:"var(--shadow-lg)", zIndex:"var(--z-dropdown)",
          animation:"slideUp 0.15s ease" }}>
          {content}
        </div>
      )}
    </div>
  );
}
