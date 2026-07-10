"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import ReactDOM from "react-dom";

export interface ColumnDef {
  key:     string;
  label:   string;
  visible: boolean;
  order:   number;
  width?:  number;
}

interface Props {
  columns:  ColumnDef[];
  onChange: (columns: ColumnDef[]) => void;
  onReset?: () => void;
}

export default function EnterpriseColumnManager({ columns, onChange, onReset }: Props) {
  const [open,   setOpen]   = useState(false);
  const [pos,    setPos]    = useState({ top: 0, left: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);

  const toggle = (key: string) =>
    onChange(columns.map(c => c.key === key ? { ...c, visible: !c.visible } : c));

  const visibleCount = columns.filter(c => c.visible).length;

  const handleOpen = useCallback(() => {
    if (!open && btnRef.current) {
      const rect   = btnRef.current.getBoundingClientRect();
      const menuW  = 220;
      const left   = Math.max(8, Math.min(rect.right - menuW, window.innerWidth - menuW - 8));
      setPos({ top: rect.bottom + 4, left });
    }
    setOpen(o => !o);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const panel = open && typeof document !== "undefined"
    ? ReactDOM.createPortal(
        <>
          {/* backdrop */}
          <div
            style={{ position: "fixed", inset: 0, zIndex: 9998 }}
            onClick={() => setOpen(false)}
          />
          {/* panel */}
          <div style={{
            position: "fixed",
            top: pos.top, left: pos.left,
            zIndex: 9999, minWidth: 220,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            boxShadow: "0 8px 28px rgba(0,0,0,0.13), 0 2px 8px rgba(0,0,0,0.07)",
            padding: 14,
            display: "flex", flexDirection: "column", gap: 6,
          }}>
            <p style={{
              fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.07em",
              paddingBottom: 8, borderBottom: "1px solid var(--border)", margin: 0,
            }}>
              Visible Columns
            </p>
            {[...columns].sort((a, b) => a.order - b.order).map(c => (
              <label key={c.key} style={{
                display: "flex", alignItems: "center", gap: 8, fontSize: 13,
                color: "var(--text-primary)", cursor: "pointer",
              }}>
                <input
                  type="checkbox"
                  checked={c.visible}
                  onChange={() => toggle(c.key)}
                  style={{ width: 14, height: 14, accentColor: "var(--brand)", cursor: "pointer" }}
                />
                {c.label}
              </label>
            ))}
            {onReset && (
              <button
                onClick={() => { onReset(); setOpen(false); }}
                style={{
                  marginTop: 4, paddingTop: 8, borderTop: "1px solid var(--border)",
                  fontSize: 11, color: "var(--danger-text, #dc2626)", background: "none",
                  border: "none", cursor: "pointer", textAlign: "left", fontFamily: "inherit",
                }}
              >
                Reset to defaults
              </button>
            )}
          </div>
        </>,
        document.body
      )
    : null;

  return (
    <div style={{ position: "relative" }}>
      <button
        ref={btnRef}
        onClick={handleOpen}
        style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          height: 34, padding: "0 12px", fontSize: 12, borderRadius: 8,
          border: "1px solid var(--border)",
          background: open ? "var(--surface-sunken)" : "var(--surface)",
          color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
          transition: "background 0.12s",
        }}
        onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
        onMouseLeave={e => { if (!open) e.currentTarget.style.background = "var(--surface)"; }}
      >
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
        </svg>
        Columns
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          ({visibleCount}/{columns.length})
        </span>
      </button>
      {panel}
    </div>
  );
}
