import { useStartupContext } from "./startup-context";
import type { StartupSnapshot } from "./startup-types";

export interface UseStartupResult {
  snapshot: StartupSnapshot;
  retry: () => void;
}

/** The sanctioned way for screens/components to read startup state — never import startup-service.ts directly from a screen. */
export function useStartup(): UseStartupResult {
  return useStartupContext();
}
