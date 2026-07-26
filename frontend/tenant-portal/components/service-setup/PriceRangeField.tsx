"use client";
import React, { useId, useState } from "react";
import { Btn } from "../shared/ui";

/** Tenant-owned min/max price input. Never labeled "Admin"/"Platform" price
 * -- every value here belongs to the tenant. No admin floor/ceiling is ever
 * displayed (per the platform's admin-never-sets-price rule).
 *
 * Accessibility: every input always has a real accessible name via
 * aria-label, even when `label` is "" (used when this field is embedded
 * inside a card that already provides its own visible heading, e.g.
 * PricingInheritanceCard) -- a placeholder alone is not an accessible label. */
export function PriceRangeField({ label, min, max, onSave, saving }: {
  label: string; min: number | null; max: number | null;
  onSave: (min: number, max: number) => void; saving?: boolean;
}) {
  const [localMin, setLocalMin] = useState(min?.toString() ?? "");
  const [localMax, setLocalMax] = useState(max?.toString() ?? "");
  const dirty = localMin !== (min?.toString() ?? "") || localMax !== (max?.toString() ?? "");
  const valid = localMin !== "" && localMax !== "" && Number(localMin) <= Number(localMax);
  const invalid = localMin !== "" && localMax !== "" && Number(localMin) > Number(localMax);
  const errorId = useId();
  const namePrefix = label ? `${label} — ` : "";

  return (
    <div>
      {label && (
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
          {label}
        </label>
      )}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="number" value={localMin} onChange={e => setLocalMin(e.target.value)} placeholder="Min ₹"
          aria-label={`${namePrefix}Minimum price`} aria-invalid={invalid} aria-describedby={invalid ? errorId : undefined}
          style={{ width: 100, height: 34, borderRadius: 7, border: "1px solid var(--border)", background: "var(--input-bg)",
            color: "var(--text-primary)", fontSize: 13, padding: "0 8px", boxSizing: "border-box" }} />
        <span aria-hidden style={{ color: "var(--text-tertiary)" }}>–</span>
        <input type="number" value={localMax} onChange={e => setLocalMax(e.target.value)} placeholder="Max ₹"
          aria-label={`${namePrefix}Maximum price`} aria-invalid={invalid} aria-describedby={invalid ? errorId : undefined}
          style={{ width: 100, height: 34, borderRadius: 7, border: "1px solid var(--border)", background: "var(--input-bg)",
            color: "var(--text-primary)", fontSize: 13, padding: "0 8px", boxSizing: "border-box" }} />
        {dirty && valid && (
          <Btn size="sm" loading={saving} onClick={() => onSave(Number(localMin), Number(localMax))}>Save</Btn>
        )}
      </div>
      {invalid && (
        <p id={errorId} role="alert" style={{ color: "var(--danger-text)", fontSize: 11, margin: "4px 0 0" }}>
          Minimum cannot exceed maximum.
        </p>
      )}
    </div>
  );
}
