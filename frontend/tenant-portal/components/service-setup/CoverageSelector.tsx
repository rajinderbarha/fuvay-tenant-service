"use client";
import React, { useRef } from "react";
import type { CoverageMode } from "../../lib/api";

/** Coverage mode picker (spec section 10/12): All / Selected only / All
 * except selected. Coverage and price are deliberately kept as separate
 * concerns -- this component only decides WHICH values are supported;
 * pricing (inherited vs custom) is a different step entirely.
 *
 * Accessibility: implements the standard roving-tabindex radiogroup pattern
 * (arrow keys move selection, only the checked option is Tab-stoppable) --
 * required for a custom role="radio" group, not optional polish. */
export function CoverageSelector({ label, mode, onChange, disabled }: {
  label: string; mode: CoverageMode; onChange: (m: CoverageMode) => void; disabled?: boolean;
}) {
  const OPTIONS: { value: CoverageMode; label: string; hint: string }[] = [
    { value: "all", label: "All", hint: `Support every ${label.toLowerCase()}` },
    { value: "selected", label: "Selected only", hint: `Pick exactly which ${label.toLowerCase()}s you support` },
    { value: "all_except", label: "All except selected", hint: `Support all ${label.toLowerCase()}s except a few` },
  ];
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  function handleKeyDown(e: React.KeyboardEvent, index: number) {
    if (disabled) return;
    let nextIndex: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") nextIndex = (index + 1) % OPTIONS.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") nextIndex = (index - 1 + OPTIONS.length) % OPTIONS.length;
    else if (e.key === "Home") nextIndex = 0;
    else if (e.key === "End") nextIndex = OPTIONS.length - 1;
    if (nextIndex !== null) {
      e.preventDefault();
      onChange(OPTIONS[nextIndex].value);
      buttonRefs.current[nextIndex]?.focus();
    }
  }

  return (
    <div role="radiogroup" aria-label={`${label} coverage`} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {OPTIONS.map((o, i) => {
        const checked = mode === o.value;
        return (
          <button key={o.value} ref={el => { buttonRefs.current[i] = el; }}
            type="button" role="radio" aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            disabled={disabled} title={o.hint}
            onClick={() => onChange(o.value)}
            onKeyDown={e => handleKeyDown(e, i)}
            style={{
              padding: "8px 14px", borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: disabled ? "default" : "pointer",
              border: `2px solid ${checked ? "var(--accent)" : "var(--border)"}`,
              background: checked ? "var(--accent)" : "var(--surface)",
              color: checked ? "#fff" : "var(--text-primary)",
              fontFamily: "inherit",
            }}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
