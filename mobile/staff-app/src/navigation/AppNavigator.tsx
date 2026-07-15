import React from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { LoginScreen }     from "../screens/LoginScreen";
import { JobDetailScreen } from "../screens/JobDetailScreen";
import { ChatRoomScreen }  from "../screens/ChatRoomScreen";
import { NotificationsScreen } from "../screens/NotificationsScreen";
import { TabNavigator }    from "./TabNavigator";
import { theme } from "../styles/theme";

const Stack = createNativeStackNavigator();

export function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) return (
    <View style={{ flex:1, alignItems:"center", justifyContent:"center", backgroundColor:theme.colors.bg }}>
      <ActivityIndicator size="large" color={theme.colors.brand} />
    </View>
  );

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown:false }}>
        {user ? (
          // ── Authenticated stack ─────────────────────────────────────────
          <>
            <Stack.Screen name="Tabs"      component={TabNavigator} />
            <Stack.Screen name="JobDetail" component={JobDetailScreen}
              options={{ headerShown:true, title:"Job Detail",
                headerStyle:{ backgroundColor:theme.colors.surface },
                headerTintColor:theme.colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" } }}
            />
            <Stack.Screen name="ChatRoom" component={ChatRoomScreen}
              options={({ route }) => ({
                headerShown:true,
                title: (route.params as { title:string }).title ?? "Chat",
                headerStyle:{ backgroundColor:theme.colors.surface },
                headerTintColor:theme.colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" },
              })}
            />
            <Stack.Screen name="Notifications" component={NotificationsScreen}
              options={{ headerShown:true, title:"Notifications",
                headerStyle:{ backgroundColor:theme.colors.surface },
                headerTintColor:theme.colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" } }}
            />
          </>
        ) : (
          // ── Unauthenticated ─────────────────────────────────────────────
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
