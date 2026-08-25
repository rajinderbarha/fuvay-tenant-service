"use client";
/**
 * Column visibility picker for EnterpriseDataGrid.
 *
 * Like EnterpriseFilterBar, this was written in Tailwind utilities in an app
 * that has no Tailwind. The most visible consequence was the trigger icon:
 * its `w-4 h-4` never applied, so the inline SVG rendered at its intrinsic
 * size and blew up into a huge black glyph next to the filters. The dropdown
 * was equally unstyled (`absolute right-0 … bg-white border rounded-xl` all
 * inert), so it rendered as a plain unpositioned list in the page flow.
 *
 * Rewritten with inline styles over the CSS design tokens, matching the rest
 * of the portal and following the theme.
 */
import { useState } from "react";
import { Columns3, RotateCcw } from "lucide-react";

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
  const [open, setOpen] = useState(false);
  const toggle = (key: string) =>
    onChange(columns.map(c => (c.key === key ? { ...c, visible: !c.visible } : c)));
  const visibleCount = columns.filter(c => c.visible).length;

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          height: 34, padding: "0 12px", fontSize: 12, borderRadius: 8,
          border: "1px solid var(--border)", background: "var(--surface)",
          color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
          whiteSpace: "nowrap",
        }}
      >
        <Columns3 size={14}/>
        Columns
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          ({visibleCount}/{columns.length})
        </span>
      </button>

      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 10 }} onClick={() => setOpen(false)}/>
          <div style={{
            position: "absolute", right: 0, top: "100%", marginTop: 4, zIndex: 20,
            minWidth: 210, maxHeight: 320, overflowY: "auto",
            background: "var(--surface-elevated)", border: "1px solid var(--border)",
            borderRadius: 12, boxShadow: "var(--shadow-lg)", padding: 10,
          }}>
            <p style={{
              fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
              color: "var(--text-tertiary)", margin: "0 0 8px", paddingBottom: 8,
              borderBottom: "1px solid var(--border)",
            }}>
              Visible columns
            </p>
            {/* `columns.sort()` mutated the caller's array in place, which can
                reorder the grid's own state unexpectedly; copy before sorting. */}
            {[...columns].sort((a, b) => a.order - b.order).map(c => (
              <label
                key={c.key}
                style={{
                  display: "flex", alignItems: "center", gap: 8, fontSize: 13,
                  color: "var(--text-primary)", cursor: "pointer", padding: "5px 2px",
                }}
              >
                <input type="checkbox" checked={c.visible} onChange={() => toggle(c.key)}/>
                {c.label}
              </label>
            ))}
            {onReset && (
              <button
                onClick={() => { onReset(); setOpen(false); }}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 5,
                  width: "100%", marginTop: 8, paddingTop: 8, paddingBottom: 2,
                  borderTop: "1px solid var(--border)", border: "none", borderRadius: 0,
                  background: "none", color: "var(--text-tertiary)", fontSize: 12,
                  cursor: "pointer", fontFamily: "inherit",
                }}
              >
                <RotateCcw size={11}/> Reset to defaults
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
