import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { renderWithProviders } from "./renderWithProviders";
import { PublicStackParamList } from "../navigation/routeTypes";

const Stack = createNativeStackNavigator<PublicStackParamList>();

/** Renders a single auth screen inside a real (isolated) native-stack
 * navigator so `useNavigation`/`useRoute` work exactly as in the app,
 * without pulling in the whole RootNavigator/session machinery. */
export function renderAuthScreen<Name extends keyof PublicStackParamList>(
  name: Name,
  Component: React.ComponentType,
  params?: PublicStackParamList[Name],
) {
  return renderWithProviders(
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name={name} component={Component} initialParams={params as object | undefined} />
      </Stack.Navigator>
    </NavigationContainer>,
  );
}
