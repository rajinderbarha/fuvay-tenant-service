"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "serviceos-admin-theme";
type Mode = "light" | "dark";

export function useTheme() {
  const [theme, setThemeState] = useState<Mode>("light");
  useEffect(() => {
    const stored = localStorage.getItem(KEY) as Mode | null;
    const pref   = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    const init   = stored ?? pref;
    setThemeState(init);
    document.documentElement.setAttribute("data-theme", init);
  }, []);
  const setTheme = useCallback((m: Mode) => {
    setThemeState(m);
    document.documentElement.setAttribute("data-theme", m);
    localStorage.setItem(KEY, m);
  }, []);
  const toggle = useCallback(() => setTheme(theme === "light" ? "dark" : "light"), [theme, setTheme]);
  return { theme, setTheme, toggle, isDark: theme === "dark" };
}
