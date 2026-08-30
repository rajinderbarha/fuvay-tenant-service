import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { AppProviders } from "../providers/AppProviders";
import { RootNavigator } from "../navigation/RootNavigator";
import { navigationRef } from "../navigation/navigationRef";
import { logBuildFingerprint } from "../config/buildFingerprint";
import { useFuvayFonts } from "../design-system/useFuvayFonts";

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
  // Fuvay v2 typefaces. Deliberately NOT gated on: React Native falls back
  // to the system font for a family that is not yet registered, so rendering
  // immediately shows correctly-laid-out text that swaps to Barlow a frame
  // later -- strictly better than holding a blank screen on a font download.
  useFuvayFonts();

  return (
    <AppProviders>
      <NavigationContainer ref={navigationRef}>
        <RootNavigator />
      </NavigationContainer>
    </AppProviders>
  );
}
