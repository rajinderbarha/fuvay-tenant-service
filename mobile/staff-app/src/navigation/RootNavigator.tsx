import React, { useEffect, useRef } from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RootStackParamList } from "./routeTypes";
import { AuthNavigator } from "./AuthNavigator";
import { AppTabs } from "./AppTabs";
import { JobExecutionNavigator } from "./JobExecutionNavigator";
import { RestrictedStateNavigator } from "./RestrictedStateNavigator";
import { FoundationSplash } from "../root/FoundationSplash";
import { useSession, useRootDestination } from "./session/SessionProvider";
import { navigationRef } from "./navigationRef";
import { destinationSignature, resetStateFor } from "./rootDestinationReset";
import { JobExecutionStackParamList } from "./routeTypes";
import { RootDestination } from "./guards/types";

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * Root of the navigation tree (spec section 1). Renders exactly one of
 * Bootstrap/AuthStack/AppTabs/JobExecutionStack/RestrictedStateStack at a
 * time, driven entirely by the trusted session/access state resolved in
 * SessionProvider -- never by a locally selected role. Whenever the
 * resolved destination's tree changes (login, logout, session expiry,
 * tenant/technician suspension detected mid-session), the native stack is
 * *reset* rather than pushed to, so no protected screen can remain
 * reachable via back navigation once security context has changed.
 */
export function RootNavigator() {
  const { bootstrapState } = useSession();
  const destination = useRootDestination();

  // The Stack.Navigator below only ever mounts once bootstrapState has left
  // "initializing" (see early return). Hooks still run unconditionally on
  // every render including the "initializing" ones, so a lazy useState
  // would wrongly freeze on that very first (stale, "Bootstrap") value --
  // instead this ref is deliberately populated during render, but only on
  // the first render where bootstrapState is already resolved, giving the
  // Stack.Navigator its real initial route the first time it ever mounts.
  const initialDestinationRef = useRef<RootDestination | null>(null);
  if (initialDestinationRef.current === null && bootstrapState !== "initializing") {
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

  if (bootstrapState === "initializing" || !initialDestinationRef.current) {
    return <FoundationSplash />;
  }

  const initialDestination = initialDestinationRef.current;

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName={initialDestination.tree}>
      <Stack.Screen name="Bootstrap" component={FoundationSplash} />
      <Stack.Screen
        name="AuthStack"
        component={AuthNavigator}
        initialParams={initialDestination.tree === "AuthStack" && initialDestination.reasonCode
          ? { screen: initialDestination.screen, params: { reasonCode: initialDestination.reasonCode } }
          : undefined}
      />
      <Stack.Screen name="AppTabs" component={AppTabs} />
      <Stack.Screen
        name="JobExecutionStack"
        component={JobExecutionNavigator}
        initialParams={initialDestination.tree === "JobExecutionStack" ? { screen: initialDestination.screen as keyof JobExecutionStackParamList, params: initialDestination.params } : undefined}
      />
      <Stack.Screen
        name="RestrictedStateStack"
        component={RestrictedStateNavigator}
        initialParams={initialDestination.tree === "RestrictedStateStack" ? { screen: initialDestination.screen, params: { reasonCode: initialDestination.reasonCode } } : undefined}
      />
    </Stack.Navigator>
  );
}
