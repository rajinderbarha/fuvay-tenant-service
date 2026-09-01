export type EditorialPaletteKey = "ink" | "citrus" | "coral" | "mint" | "violet" | "sky" | "sand";

export interface EditorialPalette {
  background: string;
  foreground: string;
  accent: string;
}

/** Campaign palettes are tokens because backend content chooses a palette by
 * key.  No campaign component owns colour literals. */
export const darkEditorialPalettes: Record<EditorialPaletteKey, EditorialPalette> = {
  ink: { background: "#132039", foreground: "#f7f8fc", accent: "#79a7ff" },
  citrus: { background: "#312812", foreground: "#fff8d6", accent: "#f7c948" },
  coral: { background: "#34201e", foreground: "#fff1ee", accent: "#ff8a78" },
  mint: { background: "#15302b", foreground: "#edfff9", accent: "#72d9b5" },
  violet: { background: "#28203b", foreground: "#f7f0ff", accent: "#b89bff" },
  sky: { background: "#142d3a", foreground: "#eaf9ff", accent: "#70c9ef" },
  sand: { background: "#30291f", foreground: "#fff9ef", accent: "#d8b98b" },
};

export const lightEditorialPalettes: Record<EditorialPaletteKey, EditorialPalette> = {
  ink: { background: "#0b1b35", foreground: "#ffffff", accent: "#71a3ff" },
  citrus: { background: "#fff2a8", foreground: "#291e00", accent: "#d07100" },
  coral: { background: "#ffe0da", foreground: "#341713", accent: "#d94b36" },
  mint: { background: "#ddf7ee", foreground: "#103229", accent: "#168263" },
  violet: { background: "#eae0ff", foreground: "#281943", accent: "#7046c7" },
  sky: { background: "#ddf3fc", foreground: "#102f3d", accent: "#197a9f" },
  sand: { background: "#f3e7d5", foreground: "#35291d", accent: "#936630" },
};

