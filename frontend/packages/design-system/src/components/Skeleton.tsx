import React from "react";
import { Loader2 } from "lucide-react";

export function Skeleton({ width = "100%", height = "1rem", radius = "var(--radius-sm)" }: { width?: string | number; height?: string | number; radius?: string }) {
  return <div className="ds-skeleton" style={{ width, height, borderRadius: radius }} aria-hidden="true" />;
}

export function Spinner({ size = 20, label = "Loading" }: { size?: number; label?: string }) {
  return (
    <span role="status" aria-label={label} style={{ display: "inline-flex" }}>
      <Loader2 size={size} className="ds-spin" aria-hidden="true" />
    </span>
  );
}
