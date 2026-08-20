"use client";

import type { CSSProperties } from "react";

type Tone = "auto" | "onLight" | "onDark";
type Props = { compact?: boolean; height?: number; className?: string; tone?: Tone; tagline?: boolean };

/** The "Far Away in Fare Way" tagline is ~14% of the artwork's height, so it
 *  renders about 4px tall at the 28-46px heights the shells use -- vector-sharp
 *  but far too small to resolve, which reads as a blurry smudge. Only show it
 *  where it can actually be read. */
const TAGLINE_MIN_HEIGHT = 64;

/** Official Fuvay artwork.
 *
 *  The lockup's wordmark is pure white, so it only reads on a dark surface.
 *  It used to be wrapped in a #071633 chip to guarantee that, which meant a
 *  navy box sat on top of every light surface (most visibly the tenant
 *  sidebar, which is #FFFFFF). Instead we ship a second render of the same
 *  artwork with the wordmark in brand navy -- fuvay-logo-onlight.svg -- and
 *  pick between them.
 *
 *  Both variants are always in the DOM and one is hidden in CSS, so the swap
 *  costs no hydration flash (data-theme is set on <html> before hydration).
 *  Note the visibility MUST stay in the stylesheet: an inline display on the
 *  <img> outranks these class rules and renders both logos at once.
 *
 *  tone="auto" follows the theme. Force a tone for surfaces that do not:
 *  the admin sidebar and admin login panel are navy in both themes.
 *
 *  Compact mode crops to the symbol, which is #0563FE blue in both variants.
 */
export default function FuvayLogo({
  compact = false,
  height = 34,
  className,
  tone = "auto",
  tagline = height >= TAGLINE_MIN_HEIGHT,
}: Props) {
  const base = tagline ? "/brand/fuvay-logo" : "/brand/fuvay-logo-notagline";

  // No `display` here on purpose -- see the note above.
  const imgStyle: CSSProperties = { height, width: "auto", maxWidth: "none" };
  const wrapStyle: CSSProperties = compact
    ? { width: height + 10, height, overflow: "hidden", display: "inline-block", flexShrink: 0 }
    : { display: "inline-flex", lineHeight: 0 };

  return (
    <span
      className={`fuvay-logo fuvay-${tone}${className ? ` ${className}` : ""}`}
      aria-label={compact ? "Fuvay" : undefined}
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
        src={`${base}-onlight.svg`}
        alt={compact ? "" : "Fuvay"}
        style={imgStyle}
      />
      <img
        className="fuvay-art-dark"
        src={`${base}.svg`}
        alt={compact ? "" : "Fuvay"}
        style={imgStyle}
      />
    </span>
  );
}
