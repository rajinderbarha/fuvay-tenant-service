import { RootDestination } from "./guards/types";

/**
 * Builds the React Navigation reset-state payload for a resolved
 * destination. Always a RESET, never a push -- a protected screen must
 * never remain reachable via back navigation once a higher-precedence
 * guard state has changed (session expiry, suspension, etc. -- spec
 * section 21).
 */
export function resetStateFor(destination: RootDestination) {
  switch (destination.tree) {
    case "Bootstrap":
      return { index: 0, routes: [{ name: "Bootstrap" as const }] };
    case "PublicStack":
      return { index: 0, routes: [{ name: "PublicStack" as const, params: { screen: destination.screen } }] };
    case "CustomerAppStack":
      return { index: 0, routes: [{ name: "CustomerAppStack" as const }] };
    case "ExceptionalStateStack":
      return {
        index: 0,
        routes: [{ name: "ExceptionalStateStack" as const, params: { screen: destination.screen, params: { reason: destination.reason } } }],
      };
  }
}
