import React, { useEffect, useRef } from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RootStackParamList } from "./routeTypes";
import { PreparingExperienceScreen } from "../screens/exceptional/PreparingExperienceScreen";
import { PublicNavigator } from "./PublicNavigator";
import { CustomerAppNavigator } from "./CustomerAppNavigator";
import { ExceptionalStateNavigator } from "./ExceptionalStateNavigator";
import { resolveDestination, destinationSignature } from "./guards/resolveDestination";
import { resetStateFor } from "./navigationReset";
import { navigationRef } from "./navigationRef";
import { useNavigationSnapshot } from "./useNavigationSnapshot";
import { RootDestination } from "./guards/types";

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * Root of the navigation tree (spec section 2/6). Renders exactly one of
 * Bootstrap/PublicStack/CustomerAppStack/ExceptionalStateStack at a time,
 * driven entirely by `resolveDestination(snapshot)` -- never by a screen
 * deciding to navigate itself. Whenever the resolved destination's
 * tree+screen signature changes, the stack is RESET (never pushed to), so
 * no protected screen remains reachable via back navigation once
 * security context changes (spec section 21) -- this mirrors the Staff
 * App's RootNavigator pattern exactly.
 */
export function RootNavigator() {
  const snapshot = useNavigationSnapshot();
  const destination = resolveDestination(snapshot);

  const initialDestinationRef = useRef<RootDestination | null>(null);
  if (initialDestinationRef.current === null && snapshot.bootstrap !== "initializing") {
    initialDestinationRef.current = destination;
  }
  const lastSignatureRef = useRef<string | null>(null);
  if (lastSignatureRef.current === null && initialDestinationRef.current) {
    lastSignatureRef.current = destinationSignature(initialDestinationRef.current);
  }

  useEffect(() => {
    const signature = destinationSignature(destination);
    if (signature === lastSignatureRef.current) return;
    if (!navigationRef.isReady()) return;
    lastSignatureRef.current = signature;
    navigationRef.reset(resetStateFor(destination));
  }, [destination]);

  if (snapshot.bootstrap === "initializing" || !initialDestinationRef.current) {
    return <PreparingExperienceScreen />;
  }

  const initialDestination = initialDestinationRef.current;

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName={initialDestination.tree}>
      <Stack.Screen name="Bootstrap" component={PreparingExperienceScreen} />
      <Stack.Screen
        name="PublicStack"
        component={PublicNavigator}
        initialParams={initialDestination.tree === "PublicStack" ? { screen: initialDestination.screen } : undefined}
      />
      <Stack.Screen name="CustomerAppStack" component={CustomerAppNavigator} />
      <Stack.Screen
        name="ExceptionalStateStack"
        component={ExceptionalStateNavigator}
        initialParams={
          initialDestination.tree === "ExceptionalStateStack"
            ? { screen: initialDestination.screen, params: { reason: initialDestination.reason } }
            : undefined
        }
      />
    </Stack.Navigator>
  );
}
