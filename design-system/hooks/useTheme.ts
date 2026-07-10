/**
 * useTheme — light/dark mode hook.
 * Persists to localStorage. Sets data-theme on <html>.
 * Single toggle changes every CSS variable instantly.
 */
import { useState, useEffect, useCallback } from "react";
import type { ThemeMode } from "../tokens/tokens";

const STORAGE_KEY = "serviceos-theme";

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>("light");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
    const initial = stored ?? preferred;
    setThemeState(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
    document.documentElement.setAttribute("data-theme", mode);
    localStorage.setItem(STORAGE_KEY, mode);
  }, []);

  const toggle = useCallback(() => {
    setTheme(theme === "light" ? "dark" : "light");
  }, [theme, setTheme]);

  return { theme, setTheme, toggle, isDark: theme === "dark" };
}
