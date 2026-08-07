/**
 * Per-card accent colour for the "Build with Fuvay" section.
 *
 * These cards are deliberately full-bleed brand colours rather than theme
 * surfaces: the design gives each offering its own identity colour, and the
 * same colour must read identically in light and dark mode (they are brand
 * accents, not themeable surfaces -- a "dark mode purple" would make the
 * section look like a different product).
 *
 * Hues follow the supplied circular icons for each offering (Web Development
 * navy, Software Development orange, AI & ML green, Blockchain purple), so
 * the card and its icon belong together. Offerings without supplied artwork
 * get their own distinct hue so no two cards in the section collide.
 *
 * Keyed on name because Global Services are free-text admin rows with no
 * slug or type column (app/engines/global_services/models.py). An
 * unrecognised name falls back to a deterministic pick from the same
 * palette rather than a single shared grey, so a newly-added service still
 * looks intentional.
 */
export interface GlobalServiceAccent {
  /** Card background. */
  background: string;
  /** Foreground for the title/CTA text on that background. */
  onBackground: string;
  /** Slightly translucent foreground for the supporting line. */
  onBackgroundMuted: string;
}

const WHITE = "#FFFFFF";
const WHITE_MUTED = "rgba(255,255,255,0.82)";

const PALETTE: readonly string[] = [
  "#4338CA", // indigo  -- Web Development
  "#0F766E", // teal    -- Mobile App Dev
  "#C2410C", // orange  -- Software Development
  "#6D28D9", // violet  -- Blockchain
  "#047857", // green   -- AI & ML
  "#BE185D", // pink    -- Data Analyst
];

const BY_KEYWORD: ReadonlyArray<[RegExp, string]> = [
  [/\bweb\b/i, PALETTE[0]],
  [/mobile|app\s*dev/i, PALETTE[1]],
  [/software/i, PALETTE[2]],
  [/blockchain|web3|crypto/i, PALETTE[3]],
  [/\bai\b|machine\s*learning|\bml\b/i, PALETTE[4]],
  [/data|analyt/i, PALETTE[5]],
];

function stableIndex(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % PALETTE.length;
  return h;
}

export function resolveGlobalServiceAccent(name: string | null | undefined): GlobalServiceAccent {
  const safe = name ?? "";
  const matched = BY_KEYWORD.find(([re]) => re.test(safe))?.[1];
  return {
    background: matched ?? PALETTE[stableIndex(safe)],
    onBackground: WHITE,
    onBackgroundMuted: WHITE_MUTED,
  };
}

export const GLOBAL_SERVICE_ACCENT_PALETTE = PALETTE;
