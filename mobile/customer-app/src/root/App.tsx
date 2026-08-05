import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { AppProviders } from "../providers/AppProviders";
import { RootNavigator } from "../navigation/RootNavigator";
import { navigationRef } from "../navigation/navigationRef";
import { logBuildFingerprint } from "../config/buildFingerprint";

// Dev-only: logs the API base URL this bundle was actually built against
// plus a bundle-load timestamp, so a phone showing stale/unexpected
// behavior can be checked against "is this even the current bundle,
// pointed at the current backend?" before assuming a code defect.
logBuildFingerprint();

/**
 * Root component. Phase E replaces the Phase A-C FoundationPreviewScreen
 * mount with the real navigation shell (Bootstrap / PublicStack /
 * CustomerAppStack / ExceptionalStateStack) -- FoundationPreviewScreen
 * itself is untouched and still exists for design-system QA, it is just
 * no longer the app's entry point (see src/screens/FoundationPreviewScreen.tsx).
 */
export default function App() {
  return (
    <AppProviders>
      <NavigationContainer ref={navigationRef}>
        <RootNavigator />
      </NavigationContainer>
    </AppProviders>
  );
}
