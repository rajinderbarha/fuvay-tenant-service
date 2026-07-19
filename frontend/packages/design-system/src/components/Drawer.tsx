"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  side?: "right" | "left";
  children: React.ReactNode;
}

export function Drawer({ open, onClose, title, side = "right", children }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{ position: "fixed", inset: 0, background: "var(--overlay)", zIndex: 1000, display: "flex", justifyContent: side === "right" ? "flex-end" : "flex-start" }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          width: "min(24rem, 90vw)",
          height: "100%",
          background: "var(--surface)",
          borderLeft: side === "right" ? "1px solid var(--border)" : undefined,
          borderRight: side === "left" ? "1px solid var(--border)" : undefined,
          boxShadow: "var(--shadow-overlay)",
          display: "flex",
          flexDirection: "column",
          transition: "transform var(--motion-base) var(--motion-easing)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "1rem 1.25rem", borderBottom: "1px solid var(--border)" }}>
          <h2 className="ds-text-section-title" style={{ margin: 0, color: "var(--text-primary)" }}>
            {title}
          </h2>
          <button aria-label="Close panel" onClick={onClose} className="ds-focus-visible" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}>
            <X size={18} />
          </button>
        </div>
        <div style={{ padding: "1.25rem", overflowY: "auto", flex: 1 }}>{children}</div>
      </div>
    </div>
  );
}
