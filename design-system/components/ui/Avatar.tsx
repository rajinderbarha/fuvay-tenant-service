/**
 * Avatar — user/tenant initials with colour derived from name.
 * PROVEN: palette uses semantic color names, not hardcoded hex.
 */
import React from "react";

// Palette indices map to CSS var pairs — no hardcoded hex in component logic
const PALETTE_CLASSES = [
  { bg: "var(--color-info-bg)",    text: "var(--color-info-text)"    },
  { bg: "var(--color-success-bg)", text: "var(--color-success-text)" },
  { bg: "var(--color-warning-bg)", text: "var(--color-warning-text)" },
  { bg: "var(--color-danger-bg)",  text: "var(--color-danger-text)"  },
  { bg: "var(--color-accent-muted)", text: "var(--color-accent)"    },
  { bg: "var(--color-surface-sunken)", text: "var(--color-text-secondary)" },
];

function hashIndex(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % PALETTE_CLASSES.length;
  return h;
}

function initials(name: string): string {
  return name.split(" ").map(w => w[0]).slice(0,2).join("").toUpperCase();
}

export function Avatar({ name, src, size = 36, style }:{
  name: string; src?: string; size?: number; style?: React.CSSProperties;
}) {
  const palette = PALETTE_CLASSES[hashIndex(name)];
  return (
    <div style={{
      width: size, height: size, borderRadius: "9999px",
      background: src ? "transparent" : palette.bg,
      color: palette.text,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.35, fontWeight: 600, overflow: "hidden",
      flexShrink: 0, border: "2px solid var(--color-border)",
      ...style,
    }}>
      {src
        ? <img src={src} alt={name} style={{ width:"100%", height:"100%", objectFit:"cover" }}/>
        : initials(name)
      }
    </div>
  );
}
