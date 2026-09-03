import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ExceptionalStateStackParamList } from "./routeTypes";
import { PreparingExperienceScreen } from "../screens/exceptional/PreparingExperienceScreen";
import { SessionExpiredScreen } from "../screens/exceptional/SessionExpiredScreen";
import { AccountSuspendedScreen } from "../screens/exceptional/AccountSuspendedScreen";
import { UpdateRequiredScreen } from "../screens/exceptional/UpdateRequiredScreen";
import { MaintenanceScreen } from "../screens/exceptional/MaintenanceScreen";
import { ApiUnavailableScreen } from "../screens/exceptional/ApiUnavailableScreen";
import { StorageUnavailableScreen } from "../screens/exceptional/StorageUnavailableScreen";
import { VerticalUnavailableScreen } from "../screens/exceptional/VerticalUnavailableScreen";
import { InvalidAccessScreen } from "../screens/exceptional/InvalidAccessScreen";
import { navigationRef } from "./navigationRef";
import { openHelpAndSupport, resetToPublicStack } from "./navigationActions";
import { Linking } from "react-native";
import { getCustomerStoreUrl } from "../api/appConfig/publicAppConfig";

const Stack = createNativeStackNavigator<ExceptionalStateStackParamList>();

/**
 * Owns every full-screen state that must never expose authenticated
 * customer data or tabs underneath (spec section 6/13). Actions here are
 * deliberately minimal, typed navigation calls -- no screen wires a fake
 * "success" outcome (e.g. "Update app" never fabricates a store URL; see
 * screens/exceptional/UpdateRequiredScreen.tsx).
 */
export function ExceptionalStateNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="PreparingExperience" component={PreparingExperienceScreen} />
      <Stack.Screen name="SessionExpired">
        {() => (
          <SessionExpiredScreen
            reason="session_expired"
            onGoToSignIn={() => resetToPublicStack(navigationRef)}
            onGetHelp={() => openHelpAndSupport()}
          />
        )}
      </Stack.Screen>
      <Stack.Screen name="AccountSuspended">
        {() => (
          <AccountSuspendedScreen
            onContactSupport={() => openHelpAndSupport()}
            onSignOut={() => resetToPublicStack(navigationRef)}
          />
        )}
      </Stack.Screen>
      <Stack.Screen name="UpdateRequired">
        {() => <UpdateRequiredScreen onUpdate={() => {
          const url = getCustomerStoreUrl() ?? "https://fuvay.com/contact/";
          void Linking.openURL(url);
        }} />}
      </Stack.Screen>
      <Stack.Screen name="Maintenance">
        {() => <MaintenanceScreen onTryAgain={() => { /* Phase F wires a real retry against bootstrap config */ }} />}
      </Stack.Screen>
      <Stack.Screen name="ApiUnavailable">
        {() => <ApiUnavailableScreen onTryAgain={() => { /* Phase F wires a real retry against the API client */ }} />}
      </Stack.Screen>
      <Stack.Screen name="StorageUnavailable">
        {() => <StorageUnavailableScreen onTryAgain={() => { /* Phase F wires a real storage re-check */ }} />}
      </Stack.Screen>
      <Stack.Screen name="VerticalUnavailable">
        {() => (
          <VerticalUnavailableScreen
            onBackToHome={() => navigationRef.isReady() && navigationRef.reset({ index: 0, routes: [{ name: "CustomerAppStack" }] })}
            onViewAvailableServices={() => navigationRef.isReady() && navigationRef.reset({ index: 0, routes: [{ name: "CustomerAppStack" }] })}
          />
        )}
      </Stack.Screen>
      <Stack.Screen name="InvalidAccess">
        {() => <InvalidAccessScreen onSignOut={() => resetToPublicStack(navigationRef)} />}
      </Stack.Screen>
    </Stack.Navigator>
  );
}
