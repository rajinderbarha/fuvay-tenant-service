"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Btn } from "../shared/ui";

export interface ActionMenuItem {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  destructive?: boolean;
}

/** Generic labeled action-menu dropdown — replaces icon-only row actions. */
export function ActionMenu({ items }: { items: (ActionMenuItem | null | false)[] }) {
  const [open, setOpen] = useState(false);
  const visible = items.filter(Boolean) as ActionMenuItem[];
  if (visible.length === 0) return null;

  return (
    <div style={{ position: "relative" }} onClick={e => e.stopPropagation()}>
      <Btn variant="ghost" size="sm" onClick={() => setOpen(o => !o)}>
        Actions <ChevronDown size={12} />
      </Btn>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 999 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", right: 0, top: "calc(100% + 4px)", zIndex: 1000,
            background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)", minWidth: 180, overflow: "hidden",
          }}>
            {visible.map(item => (
              <button
                key={item.label}
                disabled={item.disabled}
                onClick={() => { item.onClick(); setOpen(false); }}
                style={{
                  display: "block", width: "100%", textAlign: "left", padding: "9px 16px",
                  background: "none", border: "none", cursor: item.disabled ? "not-allowed" : "pointer",
                  fontSize: 13, opacity: item.disabled ? 0.5 : 1,
                  color: item.destructive ? "var(--danger-text)" : "var(--text-primary)",
                  borderBottom: "1px solid var(--border)",
                }}>
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
