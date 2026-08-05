import { NavigationContainerRefWithCurrent } from "@react-navigation/native";
import { RootStackParamList } from "./routeTypes";

/** Shared, tiny navigation actions used by exceptional-state screens --
 * kept out of the navigator file so screens never reach into
 * `navigationRef` themselves (spec section 5: no direct component
 * navigation using raw URLs/refs scattered around). */
export function resetToPublicStack(ref: NavigationContainerRefWithCurrent<RootStackParamList>) {
  if (!ref.isReady()) return;
  ref.reset({ index: 0, routes: [{ name: "PublicStack", params: { screen: "LoginMethod" } }] });
}

/** No real support routing exists yet (Phase D `conversations.support` is
 * SOURCE_VERIFIED for the API, but no customer-app screen calls it this
 * phase) -- kept as a single named seam so a later phase wires one real
 * implementation here instead of screens each inventing their own. */
export function openHelpAndSupport(): void {
  // Intentionally a no-op placeholder this phase.
}
