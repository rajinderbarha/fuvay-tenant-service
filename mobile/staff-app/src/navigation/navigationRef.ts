import { createNavigationContainerRef } from "@react-navigation/native";
import { RootStackParamList } from "./routeTypes";

/**
 * Module-level ref so deep-link/push handlers (which run outside any
 * screen's component tree) can navigate without prop-drilling. Every
 * caller must check `navigationRef.isReady()` first -- navigating before
 * NavigationContainer mounts is a no-op at best and a crash at worst.
 */
export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export function resetRoot(state: Parameters<typeof navigationRef.reset>[0]): void {
  if (!navigationRef.isReady()) return;
  navigationRef.reset(state);
}
