export const fontFamily = {
  base: "var(--font-family-base)",
  mono: "var(--font-family-mono)",
} as const;

// Each entry maps to a `.ds-text-*` utility class in theme.css and is
// mirrored here for components that need the raw scale in JS (e.g. chart
// axis label sizing).
export const typeScale = {
  display: { size: "2.25rem", weight: 700, line: "2.75rem", tracking: "-0.02em" },
  pageTitle: { size: "1.5rem", weight: 700, line: "2rem", tracking: "-0.01em" },
  sectionTitle: { size: "1.125rem", weight: 600, line: "1.5rem", tracking: "0" },
  cardTitle: { size: "1rem", weight: 600, line: "1.375rem", tracking: "0" },
  body: { size: "0.9375rem", weight: 400, line: "1.5rem", tracking: "0" },
  bodyCompact: { size: "0.8125rem", weight: 400, line: "1.25rem", tracking: "0" },
  label: { size: "0.8125rem", weight: 500, line: "1.125rem", tracking: "0.01em" },
  helper: { size: "0.75rem", weight: 400, line: "1rem", tracking: "0" },
  caption: { size: "0.6875rem", weight: 500, line: "0.875rem", tracking: "0.02em" },
  badge: { size: "0.6875rem", weight: 600, line: "1rem", tracking: "0.02em" },
  tableHeader: { size: "0.6875rem", weight: 600, line: "1rem", tracking: "0.04em" },
  tableCell: { size: "0.875rem", weight: 400, line: "1.25rem", tracking: "0" },
  numeric: { size: "0.9375rem", weight: 600, line: "1.25rem", tracking: "0", family: "mono" },
  code: { size: "0.8125rem", weight: 400, line: "1.25rem", tracking: "0", family: "mono" },
} as const;

export type TypeScaleKey = keyof typeof typeScale;
