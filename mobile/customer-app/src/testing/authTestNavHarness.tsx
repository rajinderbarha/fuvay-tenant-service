import React from "react";
import { Text } from "react-native";
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
  /**
   * Extra routes this screen can navigate TO, each rendering a marker.
   *
   * With one screen registered, `navigation.navigate("Somewhere")` is a silent no-op,
   * so a test asserting "it moves on after success" passes whether or not it does.
   * Registering the destination makes arrival observable without pulling in the real
   * screen and everything it loads.
   */
  destinations?: Partial<Record<keyof PublicStackParamList, string>>,
) {
  return renderWithProviders(
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name={name} component={Component} initialParams={params as object | undefined} />
        {Object.entries(destinations ?? {}).map(([routeName, marker]) => (
          <Stack.Screen
            key={routeName}
            name={routeName as keyof PublicStackParamList}
            component={() => <Text>{marker}</Text>}
          />
        ))}
      </Stack.Navigator>
    </NavigationContainer>,
  );
}
