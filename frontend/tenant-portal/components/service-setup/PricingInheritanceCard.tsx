"use client";
import React from "react";
import { Badge, Btn } from "../shared/ui";
import { PriceRangeField } from "./PriceRangeField";

/** Represents ONE priceable row (a type, or a brand within a type) with
 * clear inheritance: shows the resolved price, whether it's inherited or
 * custom, and lets the tenant add/remove an override. Never computes
 * resolution itself -- `resolved` always comes from the backend resolver. */
export function PricingInheritanceCard({
  name, resolved, hasOwnOverride, onSaveOverride, onRemoveOverride, saving,
}: {
  name: string;
  resolved: { resolved: boolean; minimum_price?: number; maximum_price?: number; source?: string } | null;
  hasOwnOverride: boolean;
  onSaveOverride: (min: number, max: number) => void;
  onRemoveOverride?: () => void;
  saving?: boolean;
}) {
  const badge = !resolved || !resolved.resolved
    ? { label: "Not Priced", variant: "warning" as const }
    : hasOwnOverride
    ? { label: "Custom", variant: "info" as const }
    : { label: "Inherited", variant: "muted" as const };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
      padding: "12px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
          <p style={{ margin: 0, fontWeight: 600, fontSize: 13 }}>{name}</p>
          <Badge variant={badge.variant} size="sm">{badge.label}</Badge>
        </div>
        <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>
          {resolved?.resolved
            ? `${hasOwnOverride ? "Custom price" : "Using inherited price"}: ₹${resolved.minimum_price}–₹${resolved.maximum_price}`
            : "No price resolves yet for this combination."}
        </p>
      </div>
      {hasOwnOverride ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
          <PriceRangeField label="" min={resolved?.minimum_price ?? null} max={resolved?.maximum_price ?? null}
            onSave={onSaveOverride} saving={saving} />
          {onRemoveOverride && <Btn size="xs" variant="ghost" onClick={onRemoveOverride}>Remove override</Btn>}
        </div>
      ) : (
        <Btn size="sm" variant="secondary" onClick={() => onSaveOverride(resolved?.minimum_price ?? 0, resolved?.maximum_price ?? 0)}>
          Add custom price
        </Btn>
      )}
    </div>
  );
}
