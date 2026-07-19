"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "serviceos-theme";

interface ThemeContextValue {
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setPreference: (pref: ThemePreference) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function resolve(pref: ThemePreference): ResolvedTheme {
  if (pref === "system") {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return pref;
}

/**
 * Inline script string to inject via <script dangerouslySetInnerHTML> in the
 * document <head>, BEFORE hydration, so `data-theme` is set before first
 * paint (avoids flash-of-wrong-theme). Framework-agnostic — works in any
 * Next.js app root layout.
 */
export const themeInitScript = `
(function() {
  try {
    var stored = localStorage.getItem("${STORAGE_KEY}");
    var pref = stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
    var resolved = pref === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : pref;
    document.documentElement.setAttribute("data-theme", resolved);
  } catch (e) {}
})();
`;

export function ThemeProvider({
  children,
  defaultPreference = "system",
}: {
  children: React.ReactNode;
  defaultPreference?: ThemePreference;
}) {
  const [preference, setPreferenceState] = useState<ThemePreference>(defaultPreference);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    const initial = (stored as ThemePreference) || defaultPreference;
    setPreferenceState(initial);
    setResolvedTheme(resolve(initial));
  }, [defaultPreference]);

  useEffect(() => {
    const resolved = resolve(preference);
    setResolvedTheme(resolved);
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", resolved);
    }
  }, [preference]);

  useEffect(() => {
    if (preference !== "system" || typeof window === "undefined") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setResolvedTheme(resolve("system"));
    mql.addEventListener?.("change", handler);
    return () => mql.removeEventListener?.("change", handler);
  }, [preference]);

  const setPreference = useCallback((pref: ThemePreference) => {
    setPreferenceState(pref);
    try {
      window.localStorage.setItem(STORAGE_KEY, pref);
    } catch {
      /* localStorage unavailable (private mode / SSR) — theme just won't persist */
    }
  }, []);

  const toggle = useCallback(() => {
    setPreference(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setPreference]);

  const value = useMemo(
    () => ({ preference, resolvedTheme, setPreference, toggle }),
    [preference, resolvedTheme, setPreference, toggle]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
