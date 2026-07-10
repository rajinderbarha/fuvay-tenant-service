"use client";
import React, { useState, useRef } from "react";
export interface TooltipProps { content: React.ReactNode; children: React.ReactElement; side?: "top"|"bottom"|"left"|"right"; delay?: number; }
export function Tooltip({ content, children, side = "top", delay = 400 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState({ top:0, left:0 });
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const ref   = useRef<HTMLSpanElement>(null);
  function show() {
    timer.current = setTimeout(() => {
      if (!ref.current) return;
      const r = ref.current.getBoundingClientRect();
      const tp = {
        top:    side==="bottom" ? r.bottom+6 : side==="top" ? r.top-34 : r.top+r.height/2-14,
        left:   side==="right"  ? r.right+6  : side==="left" ? r.left-160 : r.left+r.width/2,
      };
      setPos(tp); setVisible(true);
    }, delay);
  }
  function hide() { clearTimeout(timer.current); setVisible(false); }
  return (
    <>
      <span ref={ref} onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}
        style={{ display:"inline-flex" }}>
        {children}
      </span>
      {visible && (
        <div role="tooltip" style={{ position:"fixed", top:pos.top, left:pos.left,
          transform: side==="top"||side==="bottom" ? "translateX(-50%)" : undefined,
          background:"var(--color-brand-800)", color:"var(--color-text-on-brand)",
          fontSize:"var(--text-xs)", fontWeight:500, padding:"5px 10px",
          borderRadius:"var(--radius-sm)", boxShadow:"var(--shadow-md)",
          zIndex:"var(--z-tooltip)", whiteSpace:"nowrap",
          pointerEvents:"none", animation:"scaleIn 0.15s ease" }}>
          {content}
        </div>
      )}
    </>
  );
}
