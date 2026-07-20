import { useThemeContext } from "./theme-provider";
import type { AppTheme, ThemeMode, ThemePreference } from "./theme-types";

export interface UseAppThemeResult {
  theme: AppTheme;
  mode: ThemeMode;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
  isHydrated: boolean;
}

/** The only supported way to read semantic tokens or the resolved color mode. */
export function useAppTheme(): UseAppThemeResult {
  return useThemeContext();
}
