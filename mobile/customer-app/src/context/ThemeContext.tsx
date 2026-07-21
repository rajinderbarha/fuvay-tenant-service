import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Appearance, ColorSchemeName } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { buildTheme, Theme } from "../styles/theme";

// UX-07 Round 4 Pass 2: real System/Light/Dark theme contract.
// Persists the user's choice so there is no flash-of-wrong-theme after the
// preference is loaded once (first launch briefly uses the system scheme
// while AsyncStorage is read -- this is the standard RN pattern since there
// is no synchronous storage read available before first paint).
export type ThemePreference = "system" | "light" | "dark";

const STORAGE_KEY = "customer_app_theme_preference";

interface ThemeContextValue {
  theme: Theme;
  mode: "light" | "dark";
  preference: ThemePreference;
  setPreference: (p: ThemePreference) => void;
  isLoaded: boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolveMode(preference: ThemePreference, systemScheme: ColorSchemeName): "light" | "dark" {
  if (preference === "light") return "light";
  if (preference === "dark") return "dark";
  return systemScheme === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [systemScheme, setSystemScheme] = useState<ColorSchemeName>(Appearance.getColorScheme() ?? "light");
  const [isLoaded, setIsLoaded] = useState(false);

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

  const setPreference = (p: ThemePreference) => {
    setPreferenceState(p);
    AsyncStorage.setItem(STORAGE_KEY, p).catch(() => {});
  };

  const mode = resolveMode(preference, systemScheme);
  const themeObj = useMemo(() => buildTheme(mode), [mode]);

  const value: ThemeContextValue = { theme: themeObj, mode, preference, setPreference, isLoaded };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
