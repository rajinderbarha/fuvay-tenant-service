import React from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { useAppTheme } from "../context/ThemeContext";
import { LoginScreen }     from "../screens/LoginScreen";
import { JobDetailScreen } from "../screens/JobDetailScreen";
import { ChatRoomScreen }  from "../screens/ChatRoomScreen";
import { NotificationsScreen } from "../screens/NotificationsScreen";
import { RoleAwareTabNavigator } from "./ux05/RoleAwareTabNavigator";
import { PartsRequestShowcaseScreen } from "../screens/ux05/PartsRequestShowcaseScreen";
import { InspectionChecklistShowcaseScreen } from "../screens/ux05/InspectionChecklistShowcaseScreen";
import { JobNotesMediaShowcaseScreen } from "../screens/ux05/JobNotesMediaShowcaseScreen";
import { StaffPartsApprovalShowcaseScreen } from "../screens/ux05/StaffPartsApprovalShowcaseScreen";
import { CurrentJobScreen } from "../screens/ux05/CurrentJobScreen";
import { QuoteShowcaseScreen } from "../screens/ux05/QuoteShowcaseScreen";
import { OfflineStatesShowcaseScreen } from "../screens/ux05/OfflineStatesShowcaseScreen";
import { SystemStatesShowcaseScreen } from "../screens/ux05/SystemStatesShowcaseScreen";
import { ThemeShowcaseScreen } from "../screens/ux05/ThemeShowcaseScreen";
import { LocalizationShowcaseScreen } from "../screens/ux05/LocalizationShowcaseScreen";
import { NetworkStatusBanner } from "../components/ux05/NetworkStatusBanner";
import { useNetworkStatus } from "../hooks/useNetworkStatus";

const Stack = createNativeStackNavigator();

export function AppNavigator() {
  const { user, loading } = useAuth();
  // UX-05 Round 5: colors now come from useAppTheme() (reactive light/dark),
  // not the static `theme.colors` import -- this is the navigator-chrome
  // half of the dark-theme mechanism (header/tab-bar backgrounds, the React
  // Navigation `theme` prop that drives screen-transition backgrounds).
  const { colors, scheme } = useAppTheme();
  // UX-05 Round 4: real network-state banner, mounted once above every
  // screen so it shows for actual connectivity changes, not just in the
  // dev showcase. See hooks/useNetworkStatus.ts for the honest native-vs-
  // web capability boundary (real on Expo web, always-online on native
  // until a NetInfo dependency is added).
  const networkStatus = useNetworkStatus();

  const navTheme = scheme === "dark"
    ? { ...DarkTheme, colors: { ...DarkTheme.colors, primary:colors.brand, background:colors.bg, card:colors.surface, text:colors.textPrimary, border:colors.border } }
    : { ...DefaultTheme, colors: { ...DefaultTheme.colors, primary:colors.brand, background:colors.bg, card:colors.surface, text:colors.textPrimary, border:colors.border } };

  if (loading) return (
    <View style={{ flex:1, alignItems:"center", justifyContent:"center", backgroundColor:colors.bg }}>
      <ActivityIndicator size="large" color={colors.brand} />
    </View>
  );

  return (
    <NavigationContainer theme={navTheme}>
      <View style={{ flex:1, backgroundColor:colors.bg }}>
        <NetworkStatusBanner state={networkStatus} />
        <View style={{ flex:1 }}>
      <Stack.Navigator screenOptions={{ headerShown:false }}>
        {user ? (
          // ── Authenticated stack ─────────────────────────────────────────
          <>
            {/* UX-05: role-aware tab set replaces the single undifferentiated
                TabNavigator -- see navigation/ux05/RoleAwareTabNavigator.tsx.
                TabNavigator itself is left in place (not deleted) in case
                anything else still imports it directly. */}
            <Stack.Screen name="Tabs"      component={RoleAwareTabNavigator} />
            <Stack.Screen name="JobDetail" component={JobDetailScreen}
              options={{ headerShown:true, title:"Job Detail",
                headerStyle:{ backgroundColor:colors.surface },
                headerTintColor:colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" } }}
            />
            <Stack.Screen name="ChatRoom" component={ChatRoomScreen}
              options={({ route }) => ({
                headerShown:true,
                title: (route.params as { title:string }).title ?? "Chat",
                headerStyle:{ backgroundColor:colors.surface },
                headerTintColor:colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" },
              })}
            />
            <Stack.Screen name="Notifications" component={NotificationsScreen}
              options={{ headerShown:true, title:"Notifications",
                headerStyle:{ backgroundColor:colors.surface },
                headerTintColor:colors.textPrimary,
                headerTitleStyle:{ fontWeight:"700" } }}
            />
            {/* UX-05 dev-only showcases (workstream 32) -- reachable only by
                direct navigation.navigate() call, never linked from
                production nav/tabs. __DEV__-style markers live in each
                screen's own MOCK_DESIGN_ONLY note, not a route guard, since
                Expo strips nothing here automatically. */}
            <Stack.Screen name="ShowcasePartsRequest" component={PartsRequestShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Parts Request" }} />
            <Stack.Screen name="ShowcaseInspectionChecklist" component={InspectionChecklistShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Inspection & Checklist" }} />
            <Stack.Screen name="ShowcaseJobNotesMedia" component={JobNotesMediaShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Notes & Media" }} />
            <Stack.Screen name="ShowcaseStaffPartsApproval" component={StaffPartsApprovalShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Staff Parts Approval" }} />
            <Stack.Screen name="CurrentJob" component={CurrentJobScreen}
              options={{ headerShown:true, title:"Current Job" }} />
            <Stack.Screen name="ShowcaseQuote" component={QuoteShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Quote" }} />
            <Stack.Screen name="ShowcaseOfflineStates" component={OfflineStatesShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Offline States" }} />
            <Stack.Screen name="ShowcaseSystemStates" component={SystemStatesShowcaseScreen}
              options={{ headerShown:true, title:"Dev: System States" }} />
            <Stack.Screen name="ShowcaseTheme" component={ThemeShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Theme" }} />
            <Stack.Screen name="ShowcaseLocalization" component={LocalizationShowcaseScreen}
              options={{ headerShown:true, title:"Dev: Localization" }} />
          </>
        ) : (
          // ── Unauthenticated ─────────────────────────────────────────────
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
        </View>
      </View>
    </NavigationContainer>
  );
}
