import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RestrictedStateStackParamList } from "./routeTypes";
import { RestrictedStateScreen } from "./placeholders/RestrictedStateScreen";

const Stack = createNativeStackNavigator<RestrictedStateStackParamList>();

const SCREENS: (keyof RestrictedStateStackParamList)[] = [
  "AccountPending", "AccountSuspended", "TenantSuspended", "TechnicianInactive",
  "AccessDenied", "AppUpdateRequired", "ServiceUnavailable",
];

/**
 * Restricted-state stack (spec sections 1, 10). No screen here can
 * navigate back into protected content -- the header is hidden and no
 * back gesture/button is rendered on any of these screens, since arriving
 * here always means a RootNavigator-level reset already happened.
 */
export function RestrictedStateNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, gestureEnabled: false }}>
      {SCREENS.map(name => (
        <Stack.Screen key={name} name={name}>
          {({ route }) => <RestrictedStateScreen screen={name} reasonCode={route.params.reasonCode} />}
        </Stack.Screen>
      ))}
    </Stack.Navigator>
  );
}
