import React from "react";
import { ActivityIndicator, View } from "react-native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { theme } from "../styles/theme";

// Screens
import { LoginScreen } from "../screens/LoginScreen";
import { BookingDetailScreen } from "../screens/BookingDetailScreen";
import { BookServiceScreen } from "../screens/BookServiceScreen";
import { JobTrackingScreen } from "../screens/JobTrackingScreen";
import { ReviewScreen } from "../screens/ReviewScreen";
import { SettingsScreen } from "../screens/SettingsScreen";
import { NotificationsScreen } from "../screens/NotificationsScreen";
import { AddressBookScreen } from "../screens/AddressBookScreen";
import { ServiceHistoryScreen } from "../screens/ServiceHistoryScreen";
import { HelpSupportScreen } from "../screens/HelpSupportScreen";
import { PaymentMethodsScreen } from "../screens/PaymentMethodsScreen";
import { InvoiceScreen } from "../screens/InvoiceScreen";
import { SmartBotScreen } from "../screens/SmartBotScreen";
import { AIAssistantScreen } from "../screens/AIAssistantScreen";
import { QuoteApprovalScreen } from "../screens/QuoteApprovalScreen";
import { TabNavigator } from "./TabNavigator";
import { DesignSystemShowcaseScreen } from "../design-system/showcase/DesignSystemShowcaseScreen";

const Stack = createNativeStackNavigator();

// Shared header style
const HDR = {
  headerShown: true,
  headerStyle: { backgroundColor: theme.colors.surface },
  headerTintColor: theme.colors.textPrimary,
  headerTitleStyle: { fontWeight: "700" as const },
};

/**
 * The pre-existing (CUSTOMER-L5-00 and earlier) authenticated app stack.
 * As of CUSTOMER-L5-01 this no longer owns its own NavigationContainer —
 * RootNavigator.tsx is now the single container for the whole app, and
 * mounts this component as one nested screen ("LegacyApp") so the existing
 * login flow and all 19 pre-existing screens remain reachable rather than
 * orphaned (see docs/customer-app/navigation-architecture.md).
 */
export function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.bg }}>
        <ActivityIndicator size="large" color={theme.colors.brand} />
      </View>
    );

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {user ? (
        <>
          {/* ── Tab root ─────────────────────────────────────────────── */}
          <Stack.Screen name="Tabs" component={TabNavigator} />

          {/* ── Booking flow ─────────────────────────────────────────── */}
          {/* eslint-disable @typescript-eslint/no-explicit-any */}
          {/* These pre-existing screens declare their own navigation/route Props shape
                that predates a typed RootStackParamList (CUSTOMER-L5-00 §28 defers migrating
                them); casting at the call site avoids touching 8 screens' internals here. */}
          <Stack.Screen name="BookService" component={BookServiceScreen as any} options={{ ...HDR, title: "Book a Service" }} />
          <Stack.Screen name="BookingDetail" component={BookingDetailScreen as any} options={{ ...HDR, title: "Booking Details" }} />
          <Stack.Screen name="JobTracking" component={JobTrackingScreen as any} options={{ ...HDR, title: "Track Technician" }} />
          <Stack.Screen name="SmartBot" component={SmartBotScreen as any} options={{ headerShown: false }} />
          <Stack.Screen
            name="AIAssistant"
            component={AIAssistantScreen as any}
            options={{
              headerShown: true,
              title: "AI Assistant 🤖",
              headerStyle: { backgroundColor: theme.colors.surface },
              headerTintColor: theme.colors.textPrimary,
              headerTitleStyle: { fontWeight: "700" },
            }}
          />
          <Stack.Screen
            name="QuoteApproval"
            component={QuoteApprovalScreen as any}
            options={{
              headerShown: true,
              title: "Repair Quote",
              headerStyle: { backgroundColor: theme.colors.surface },
              headerTintColor: theme.colors.textPrimary,
              headerTitleStyle: { fontWeight: "700" },
            }}
          />
          <Stack.Screen name="Review" component={ReviewScreen as any} options={{ ...HDR, title: "Leave a Review" }} />
          <Stack.Screen name="Invoice" component={InvoiceScreen as any} options={{ ...HDR, title: "Invoice" }} />
          {/* eslint-enable @typescript-eslint/no-explicit-any */}

          {/* ── Account / settings ────────────────────────────────────── */}
          <Stack.Screen name="Settings" component={SettingsScreen} options={{ ...HDR, title: "Settings" }} />
          <Stack.Screen name="Notifications" component={NotificationsScreen} options={{ ...HDR, title: "Notifications" }} />
          <Stack.Screen name="AddressBook" component={AddressBookScreen} options={{ ...HDR, title: "Saved Addresses" }} />
          <Stack.Screen name="ServiceHistory" component={ServiceHistoryScreen} options={{ ...HDR, title: "Service History" }} />
          <Stack.Screen name="HelpSupport" component={HelpSupportScreen} options={{ ...HDR, title: "Help & Support" }} />
          <Stack.Screen name="PaymentMethods" component={PaymentMethodsScreen} options={{ ...HDR, title: "Payment Methods" }} />

          {/* ── Development-only (CUSTOMER-L5-00) — never reachable in production ── */}
          {__DEV__ ? (
            <Stack.Screen name="DesignSystemShowcase" component={DesignSystemShowcaseScreen} options={{ ...HDR, title: "Design System Showcase (dev)" }} />
          ) : null}
        </>
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}
