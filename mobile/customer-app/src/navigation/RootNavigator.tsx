import React, { useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { linkingConfig } from "./linking-config";
import { getNavigationRefForContainer, flushQueuedIntent } from "./navigation-service";
import { useStartup } from "../app/startup/use-startup";
import { StartupScreen } from "../features/system/screens/StartupScreen";
import { StartupErrorScreen } from "../features/system/screens/StartupErrorScreen";
import { OfflineStartupScreen } from "../features/system/screens/OfflineStartupScreen";
import { MaintenanceScreen } from "../features/system/screens/MaintenanceScreen";
import { MandatoryUpdateScreen } from "../features/system/screens/MandatoryUpdateScreen";
import { UnsupportedBuildScreen } from "../features/system/screens/UnsupportedBuildScreen";
import { AppUnavailableScreen } from "../features/system/screens/AppUnavailableScreen";
import { MainNavigator } from "./MainNavigator";
import { OtpLoginScreen } from "../features/auth/screens/OtpLoginScreen";

const Stack = createNativeStackNavigator();

/**
 * The single NavigationContainer for the whole app. Renders exactly one of
 * the system gate screens or the main app area, based on the startup
 * orchestrator's decision — never both, and never a business screen while a
 * mandatory gate is active (see route-guards.ts / startup-route-resolver.ts).
 */
export function RootNavigator() {
  const { snapshot } = useStartup();
  const navigationRef = getNavigationRefForContainer();

  useEffect(() => {
    // AppState-driven startup retries can complete while already mounted —
    // flush any deep link that arrived before the container was ready.
    if (navigationRef.isReady()) flushQueuedIntent();
  }, [navigationRef, snapshot.status]);

  return (
    <NavigationContainer ref={navigationRef} linking={linkingConfig} onReady={flushQueuedIntent}>
      <Stack.Navigator screenOptions={{ headerShown: false }}>{renderStackScreens(snapshot)}</Stack.Navigator>
    </NavigationContainer>
  );
}

function renderStackScreens(snapshot: ReturnType<typeof useStartup>["snapshot"]) {
  if (snapshot.status === "idle" || snapshot.status === "running") {
    return <Stack.Screen name="Startup" component={StartupScreen} />;
  }

  if (snapshot.status === "failed") {
    return <Stack.Screen name="StartupError" component={StartupErrorScreen} />;
  }

  const routeId = snapshot.routeDecision?.routeId;

  switch (routeId) {
    case "offlineStartup":
      return <Stack.Screen name="OfflineStartup" component={OfflineStartupScreen} />;
    case "maintenance":
      return <Stack.Screen name="Maintenance" component={MaintenanceScreen} />;
    case "mandatoryUpdate":
      return <Stack.Screen name="MandatoryUpdate" component={MandatoryUpdateScreen} />;
    case "unsupportedBuild":
      return <Stack.Screen name="UnsupportedBuild" component={UnsupportedBuildScreen} />;
    case "appUnavailable":
      return <Stack.Screen name="AppUnavailable" component={AppUnavailableScreen} />;
    case "authentication":
      return <Stack.Screen name="Authentication" component={OtpLoginScreen} />;
    case "home":
      return <Stack.Screen name="Main">{() => <MainNavigator initialRouteName="Home" />}</Stack.Screen>;
    default:
      return <Stack.Screen name="Main" component={MainNavigator} />;
  }
}
