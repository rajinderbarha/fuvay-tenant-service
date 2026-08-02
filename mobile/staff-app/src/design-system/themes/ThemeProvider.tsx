import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Appearance, ColorSchemeName, AccessibilityInfo } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { buildTheme, Theme, ThemeMode } from "./buildTheme";

/**
 * System/Light/Dark theme contract (foundation spec section 9). Theme
 * preference is device/user presentation state, not a tenant-controlled
 * business setting -- plain AsyncStorage is correct here (contrast with
 * SecureStore, reserved for session/auth material in services/auth).
 */
export type ThemePreference = "system" | "light" | "dark";

const STORAGE_KEY = "staff_app_theme_preference";

interface ThemeContextValue {
  theme: Theme;
  mode: ThemeMode;
  preference: ThemePreference;
  setPreference: (p: ThemePreference) => void;
  isLoaded: boolean;
  reduceMotionEnabled: boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolveMode(preference: ThemePreference, systemScheme: ColorSchemeName): ThemeMode {
  if (preference === "light") return "light";
  if (preference === "dark") return "dark";
  return systemScheme === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [systemScheme, setSystemScheme] = useState<ColorSchemeName>(Appearance.getColorScheme() ?? "dark");
  const [isLoaded, setIsLoaded] = useState(false);
  const [reduceMotionEnabled, setReduceMotionEnabled] = useState(false);

  // First launch reads AsyncStorage before first meaningful paint isn't
  // possible synchronously in RN -- this is the standard pattern: default to
  // system scheme, then reconcile once storage resolves. `isLoaded` lets the
  // app root hold a splash frame instead of showing a theme flash.
  useEffect(() => {
    let mounted = true;
    AsyncStorage.getItem(STORAGE_KEY).then(stored => {
      if (!mounted) return;
      if (stored === "light" || stored === "dark" || stored === "system") {
        setPreferenceState(stored);
      }
      setIsLoaded(true);
    }).catch(() => { if (mounted) setIsLoaded(true); });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => setSystemScheme(colorScheme));
    return () => sub.remove();
  }, []);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotionEnabled).catch(() => {});
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", setReduceMotionEnabled);
    return () => sub.remove();
  }, []);

  const setPreference = (p: ThemePreference) => {
    setPreferenceState(p);
    AsyncStorage.setItem(STORAGE_KEY, p).catch(() => {});
  };

  const mode = resolveMode(preference, systemScheme);
  const theme = useMemo(() => buildTheme(mode), [mode]);

  const value: ThemeContextValue = { theme, mode, preference, setPreference, isLoaded, reduceMotionEnabled };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}

/** Convenience hook for components that only need reduced-motion state
 * without pulling the whole theme context. */
export function useReducedMotion(): boolean {
  return useTheme().reduceMotionEnabled;
}
