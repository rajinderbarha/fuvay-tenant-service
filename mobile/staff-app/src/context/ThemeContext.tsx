import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Appearance } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getColors, type ColorScheme } from "../styles/theme";

/**
 * UX-05 Round 5 -- real dark-theme mechanism for mobile/staff-app.
 *
 * Mirrors frontend/packages/design-system's ThemeProvider pattern
 * (preference: "light"|"dark"|"system" -> resolvedTheme, persisted across
 * restarts, system-driven by default) using React Native's real equivalents
 * of the web APIs that pattern uses:
 *   - `window.matchMedia("(prefers-color-scheme: dark)")` -> `Appearance.getColorScheme()`
 *     + `Appearance.addChangeListener` (both real RN APIs, not fabricated).
 *   - `localStorage` -> `@react-native-async-storage/async-storage` (already
 *     a real dependency of this app -- used by AuthContext).
 *
 * Consumers call `useAppTheme()` to get `{ scheme, colors, preference,
 * setPreference, toggle }` and build styles from `colors` reactively
 * (see components/ux05/* that were converted to consume this -- not every
 * screen was converted this round, see light-dark-theme-report.md for the
 * honest scope).
 */
export type ThemePreference = "light" | "dark" | "system";

const STORAGE_KEY = "serviceos_staff_theme_preference";

interface ThemeCtx {
  preference: ThemePreference;
  scheme: ColorScheme;
  colors: ReturnType<typeof getColors>;
  setPreference: (pref: ThemePreference) => void;
  toggle: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function resolveScheme(pref: ThemePreference): ColorScheme {
  if (pref === "system") return Appearance.getColorScheme() === "dark" ? "dark" : "light";
  return pref;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [scheme, setScheme] = useState<ColorScheme>(() => resolveScheme("system"));

  // Load persisted preference on mount.
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then(stored => {
      const pref = (stored === "light" || stored === "dark" || stored === "system") ? stored : "system";
      setPreferenceState(pref);
      setScheme(resolveScheme(pref));
    }).catch(() => { /* default to system on read failure */ });
  }, []);

  // React to OS-level scheme changes while preference is "system".
  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => {
      setPreferenceState(current => {
        if (current === "system") setScheme(colorScheme === "dark" ? "dark" : "light");
        return current;
      });
    });
    return () => sub.remove();
  }, []);

  const setPreference = useCallback((pref: ThemePreference) => {
    setPreferenceState(pref);
    setScheme(resolveScheme(pref));
    AsyncStorage.setItem(STORAGE_KEY, pref).catch(() => { /* non-fatal -- preference just won't persist */ });
  }, []);

  const toggle = useCallback(() => {
    setPreference(scheme === "dark" ? "light" : "dark");
  }, [scheme, setPreference]);

  const colors = useMemo(() => getColors(scheme), [scheme]);

  const value = useMemo<ThemeCtx>(() => ({ preference, scheme, colors, setPreference, toggle }),
    [preference, scheme, colors, setPreference, toggle]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppTheme must be used inside ThemeProvider");
  return ctx;
}
