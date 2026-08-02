import { RootDestination } from "./guards/types";
import { navigationRef } from "./navigationRef";

/**
 * Pure helpers extracted from RootNavigator so the reset-on-security-change
 * behavior (spec section 10) can be unit tested without mounting a full
 * NavigationContainer.
 */
export function destinationSignature(destination: RootDestination): string {
  switch (destination.tree) {
    case "AuthStack": return `AuthStack:${destination.screen}`;
    case "RestrictedStateStack": return `RestrictedStateStack:${destination.screen}:${destination.reasonCode}`;
    case "JobExecutionStack": return `JobExecutionStack:${destination.screen}:${destination.params.jobId}`;
    default: return destination.tree;
  }
}

export function resetStateFor(destination: RootDestination): Parameters<typeof navigationRef.reset>[0] {
  switch (destination.tree) {
    case "Bootstrap":
      return { index: 0, routes: [{ name: "Bootstrap" }] };
    case "AuthStack":
      // A reasonCode (e.g. SESSION_EXPIRED) is forwarded into Login's own
      // params so it can show the real "please sign in again" context --
      // omitted entirely when absent so a plain logout/first-launch reset
      // stays exactly `{ name: "AuthStack" }` (unchanged from before).
      return destination.reasonCode
        ? { index: 0, routes: [{ name: "AuthStack", params: { screen: destination.screen, params: { reasonCode: destination.reasonCode } } }] }
        : { index: 0, routes: [{ name: "AuthStack" }] };
    case "AppTabs":
      return { index: 0, routes: [{ name: "AppTabs" }] };
    case "JobExecutionStack":
      return { index: 0, routes: [{ name: "JobExecutionStack", params: { screen: destination.screen, params: destination.params } }] };
    case "RestrictedStateStack":
      return { index: 0, routes: [{ name: "RestrictedStateStack", params: { screen: destination.screen, params: { reasonCode: destination.reasonCode } } }] };
  }
}
