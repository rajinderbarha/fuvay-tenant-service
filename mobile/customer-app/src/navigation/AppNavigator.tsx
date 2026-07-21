import React from "react";
import { ActivityIndicator, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

// Screens
import { LoginScreen }             from "../screens/LoginScreen";
import { BookingDetailScreen }     from "../screens/BookingDetailScreen";
import { JobTrackingScreen }       from "../screens/JobTrackingScreen";
import { ReviewScreen }            from "../screens/ReviewScreen";
import { SettingsScreen }          from "../screens/SettingsScreen";
import { NotificationsScreen }     from "../screens/NotificationsScreen";
import { AddressBookScreen }       from "../screens/AddressBookScreen";
import { ServiceHistoryScreen }    from "../screens/ServiceHistoryScreen";
import { HelpSupportScreen }       from "../screens/HelpSupportScreen";
import { PaymentMethodsScreen }    from "../screens/PaymentMethodsScreen";
import { InvoiceScreen }           from "../screens/InvoiceScreen";
import { ServiceDetailScreen }     from "../screens/ServiceDetailScreen";
import { QuoteApprovalScreen }     from "../screens/QuoteApprovalScreen";
import { TabNavigator }            from "./TabNavigator";
// UX-06 Round 5: BookServiceScreen/SmartBotScreen/AIAssistantScreen/
// AIChatScreen deleted (not just unregistered) -- all four were fully
// superseded by DeepSeekChatScreen's real, live-verified booking/chat flow
// and called dead APIs (bookingsApi.create, aiApi -- neither ever existed).
// Keeping dead code around that calls nonexistent endpoints, even
// unreachable, is worse than deleting it. See old-scaffold-closure-report.md.

// UX-06 Round 5: a real root param list, replacing the untyped
// createNativeStackNavigator() -- this is what resolved the last remaining
// "Type '{}' is missing ... navigation, route" class of typecheck error
// across every screen with typed route params (Pattern F in
// typecheck-error-classification.md/typecheck-reconciliation.md).
export type RootStackParamList = {
  Tabs: undefined;
  BookingDetail: { bookingId:string };
  ServiceDetail: { categorySlug:string; offeringSlug:string };
  JobTracking: { jobId:string };
  QuoteApproval: { jobId:string; bookingNumber?:string };
  Review: { bookingId:string; jobId?:string };
  Invoice: { invoiceId:string };
  Settings: undefined;
  Notifications: undefined;
  AddressBook: undefined;
  ServiceHistory: undefined;
  HelpSupport: undefined;
  PaymentMethods: undefined;
  Login: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  const { user, loading } = useAuth();
  const { theme, mode, isLoaded } = useTheme();

  // Shared header style -- theme-aware, rebuilt whenever mode changes
  const HDR = {
    headerShown:      true,
    headerStyle:      { backgroundColor:theme.colors.surface },
    headerTintColor:  theme.colors.textPrimary,
    headerTitleStyle: { fontWeight:"700" as const },
  };

  // Avoid a flash-of-wrong-theme: hold the loading spinner (already
  // theme-driven) until the persisted preference has been read once.
  if (loading || !isLoaded) return (
    <View style={{ flex:1, alignItems:"center", justifyContent:"center", backgroundColor:theme.colors.bg }}>
      <ActivityIndicator size="large" color={theme.colors.brand}/>
    </View>
  );

  const navTheme = mode === "dark"
    ? { ...DarkTheme, colors: { ...DarkTheme.colors, background: theme.colors.bg, card: theme.colors.surface, text: theme.colors.textPrimary, border: theme.colors.border, primary: theme.colors.brand } }
    : { ...DefaultTheme, colors: { ...DefaultTheme.colors, background: theme.colors.bg, card: theme.colors.surface, text: theme.colors.textPrimary, border: theme.colors.border, primary: theme.colors.brand } };

  return (
    <NavigationContainer theme={navTheme}>
      <StatusBar style={mode === "dark" ? "light" : "dark"}/>
      <Stack.Navigator screenOptions={{ headerShown:false }}>
        {user ? (
          <>
            {/* ── Tab root ─────────────────────────────────────────────── */}
            <Stack.Screen name="Tabs" component={TabNavigator}/>

            {/* ── Booking flow ─────────────────────────────────────────── */}
            <Stack.Screen name="BookingDetail" component={BookingDetailScreen}
              options={{ ...HDR, title:"Booking Details" }}/>
            <Stack.Screen name="ServiceDetail" component={ServiceDetailScreen}
              options={{ ...HDR, title:"Service Details" }}/>
            <Stack.Screen name="JobTracking"   component={JobTrackingScreen}
              options={{ ...HDR, title:"Track Technician" }}/>
            <Stack.Screen name="QuoteApproval" component={QuoteApprovalScreen}
              options={{ ...HDR, title:"Repair Quote" }}/>
            <Stack.Screen name="Review"        component={ReviewScreen}
              options={{ ...HDR, title:"Leave a Review" }}/>
            <Stack.Screen name="Invoice"       component={InvoiceScreen}
              options={{ ...HDR, title:"Invoice" }}/>

            {/* ── Account / settings ────────────────────────────────────── */}
            <Stack.Screen name="Settings"       component={SettingsScreen}
              options={{ ...HDR, title:"Settings" }}/>
            <Stack.Screen name="Notifications"  component={NotificationsScreen}
              options={{ ...HDR, title:"Notifications" }}/>
            <Stack.Screen name="AddressBook"    component={AddressBookScreen}
              options={{ ...HDR, title:"Saved Addresses" }}/>
            <Stack.Screen name="ServiceHistory" component={ServiceHistoryScreen}
              options={{ ...HDR, title:"Service History" }}/>
            <Stack.Screen name="HelpSupport"    component={HelpSupportScreen}
              options={{ ...HDR, title:"Help & Support" }}/>
            <Stack.Screen name="PaymentMethods" component={PaymentMethodsScreen}
              options={{ ...HDR, title:"Payment Methods" }}/>
          </>
        ) : (
          <Stack.Screen name="Login" component={LoginScreen}/>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
