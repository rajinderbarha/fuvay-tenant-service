/**
 * Primitive color scales. Do not import this file from feature/screen code —
 * consume semantic tokens from `themes/light-theme.ts` / `dark-theme.ts` instead.
 */

export const neutral = {
  0: "#FFFFFF",
  50: "#F8FAFC",
  100: "#F1F5F9",
  200: "#E2E8F0",
  300: "#CBD5E1",
  400: "#94A3B8",
  500: "#64748B",
  600: "#475569",
  700: "#334155",
  800: "#1E293B",
  900: "#0F172A",
  950: "#020617",
} as const;

export const brand = {
  50: "#EBF6FB",
  100: "#D6EDF7",
  200: "#A9DAEF",
  300: "#6FBFE0",
  400: "#4A90D9",
  500: "#2E86AB",
  600: "#1E3A5F",
  700: "#182F4D",
  800: "#12233A",
  900: "#0C1826",
} as const;

export const blue = {
  50: "#F0F9FF",
  100: "#E0F2FE",
  300: "#7DD3FC",
  500: "#0EA5E9",
  600: "#0284C7",
  700: "#0369A1",
} as const;

export const green = {
  50: "#F0FDF4",
  100: "#DCFCE7",
  300: "#86EFAC",
  500: "#16A34A",
  600: "#15803D",
  700: "#166534",
} as const;

export const amber = {
  50: "#FFFBEB",
  100: "#FEF3C7",
  300: "#FCD34D",
  500: "#D97706",
  600: "#B45309",
  700: "#92400E",
} as const;

export const red = {
  50: "#FEF2F2",
  100: "#FEE2E2",
  300: "#FCA5A5",
  500: "#DC2626",
  600: "#B91C1C",
  700: "#991B1B",
} as const;

export const accent = {
  500: "#F59E0B",
} as const;
