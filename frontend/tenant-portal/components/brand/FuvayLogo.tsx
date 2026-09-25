"use client";

import type { CSSProperties } from "react";
import { usePlatformBranding } from "./PlatformBrandProvider";

type Tone = "auto" | "onLight" | "onDark";
type Props = { compact?: boolean; height?: number; className?: string; tone?: Tone; tagline?: boolean };

/** Official supplied green artwork: white wordmark on dark surfaces and black
 * wordmark on light surfaces. Compact sidebars crop to the original symbol.
 * Visibility stays in CSS to follow the theme without a hydration flash. */
export default function FuvayLogo({
  compact = false,
  height = 34,
  className,
  tone = "auto",
}: Props) {
  const brand = usePlatformBranding();
  // Preserve the supplied artwork, including its tagline, in every full lockup.

  // Keep display in the stylesheet so exactly one theme variant is visible.
  const imgStyle: CSSProperties = { height, width: "auto", maxWidth: "none", flexShrink: 0 };
  const wrapStyle: CSSProperties = compact
    ? { width: height * 456 / 433, height, overflow: "hidden", display: "inline-block", flexShrink: 0 }
    : { display: "inline-flex", lineHeight: 0 };

  if (compact && brand.brand_mark_url) {
    return <span className={className} aria-label={brand.short_name} style={{ display: "inline-flex", width: height, height }}>
      <img src={brand.brand_mark_url} alt="" style={{ width: height, height, objectFit: "contain", flexShrink: 0 }} />
    </span>;
  }

  return (
    <span
      className={`fuvay-logo fuvay-${tone}${className ? ` ${className}` : ""}`}
      aria-label={compact ? brand.short_name : undefined}
      style={wrapStyle}
    >
      <style>{`
        /* Default to the light-surface artwork: :root is the light palette,
           so an unset data-theme must render as light. */
        .fuvay-logo .fuvay-art-light { display: block; }
        .fuvay-logo .fuvay-art-dark  { display: none; }
        /* Higher specificity (3 classes) so it beats the defaults above. */
        [data-theme="dark"] .fuvay-auto .fuvay-art-dark  { display: block; }
        [data-theme="dark"] .fuvay-auto .fuvay-art-light { display: none; }
        /* Equal specificity to the defaults, so these must stay last. */
        .fuvay-onDark .fuvay-art-dark   { display: block; }
        .fuvay-onDark .fuvay-art-light  { display: none; }
        .fuvay-onLight .fuvay-art-light { display: block; }
        .fuvay-onLight .fuvay-art-dark  { display: none; }
      `}</style>
      <img
        className="fuvay-art-light"
        src={brand.logo_light_url ?? "/brand/fuvay-green-light.png"}
        alt={compact ? "" : brand.brand_name}
        style={imgStyle}
      />
      <img
        className="fuvay-art-dark"
        src={brand.logo_dark_url ?? "/brand/fuvay-green-dark.png"}
        alt={compact ? "" : brand.brand_name}
        style={imgStyle}
      />
    </span>
  );
}
