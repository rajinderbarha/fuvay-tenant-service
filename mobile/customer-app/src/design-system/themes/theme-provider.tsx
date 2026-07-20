import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import { useColorScheme, type ColorSchemeName } from "react-native";
import { lightTheme } from "./light-theme";
import { darkTheme } from "./dark-theme";
import type { AppTheme, ThemeMode, ThemePreference } from "./theme-types";
import { preferenceStorage } from "../../storage/preference-storage";
import { PREFERENCE_STORAGE_KEYS } from "../../storage/storage-keys";

interface ThemeContextValue {
  theme: AppTheme;
  mode: ThemeMode;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
  isHydrated: boolean;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function isThemePreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

function resolveMode(preference: ThemePreference, systemScheme: ColorSchemeName): ThemeMode {
  if (preference === "system") return systemScheme === "dark" ? "dark" : "light";
  return preference;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    preferenceStorage.getItem<ThemePreference>(PREFERENCE_STORAGE_KEYS.themePreference).then((stored) => {
      if (cancelled) return;
      // Invalid/corrupted persisted value falls back to "system" rather than crashing.
      setPreferenceState(isThemePreference(stored) ? stored : "system");
      setIsHydrated(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    void preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, next);
  }, []);

  const mode = resolveMode(preference, systemScheme);
  const theme = mode === "dark" ? darkTheme : lightTheme;

  // Stable value reference: does not change identity every render, only when
  // the resolved theme/preference actually changes.
  const value = useMemo<ThemeContextValue>(
    () => ({ theme, mode, preference, setPreference, isHydrated }),
    [theme, mode, preference, setPreference, isHydrated]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemeContext(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useThemeContext must be used within a ThemeProvider");
  return ctx;
}
