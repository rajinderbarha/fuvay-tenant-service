import React from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { theme } from "../styles/theme";

// Screens
import { LoginScreen }             from "../screens/LoginScreen";
import { BookingDetailScreen }     from "../screens/BookingDetailScreen";
import { BookServiceScreen }       from "../screens/BookServiceScreen";
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
// UX-06 Round 3 fix: these 3 screens were referenced below (SmartBot/
// AIAssistant/QuoteApproval routes) with no import anywhere in this file —
// a pre-existing "Cannot find name" ReferenceError that crashed the whole app
// at runtime the moment a logged-in user's stack tried to render (discovered
// via a real Playwright browser run against Expo web this round). Fixing the
// missing imports, not touching route structure.
import { SmartBotScreen }          from "../screens/SmartBotScreen";
import { AIAssistantScreen }       from "../screens/AIAssistantScreen";
import { QuoteApprovalScreen }     from "../screens/QuoteApprovalScreen";
import { TabNavigator }            from "./TabNavigator";

const Stack = createNativeStackNavigator();

// Shared header style
const HDR = {
  headerShown:      true,
  headerStyle:      { backgroundColor:theme.colors.surface },
  headerTintColor:  theme.colors.textPrimary,
  headerTitleStyle: { fontWeight:"700" as const },
};

export function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) return (
    <View style={{ flex:1, alignItems:"center", justifyContent:"center", backgroundColor:theme.colors.bg }}>
      <ActivityIndicator size="large" color={theme.colors.brand}/>
    </View>
  );

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown:false }}>
        {user ? (
          <>
            {/* ── Tab root ─────────────────────────────────────────────── */}
            <Stack.Screen name="Tabs" component={TabNavigator}/>

            {/* ── Booking flow ─────────────────────────────────────────── */}
            <Stack.Screen name="BookService"   component={BookServiceScreen}
              options={{ ...HDR, title:"Book a Service" }}/>
            <Stack.Screen name="BookingDetail" component={BookingDetailScreen}
              options={{ ...HDR, title:"Booking Details" }}/>
            <Stack.Screen name="ServiceDetail" component={ServiceDetailScreen}
              options={{ ...HDR, title:"Service Details" }}/>
            <Stack.Screen name="JobTracking"   component={JobTrackingScreen}
              options={{ ...HDR, title:"Track Technician" }}/>
            <Stack.Screen name="SmartBot" component={SmartBotScreen}
              options={{ headerShown:false }}/>
            <Stack.Screen name="AIAssistant" component={AIAssistantScreen}
              options={{ headerShown:true, title:"AI Assistant 🤖",
                headerStyle:{backgroundColor:theme.colors.surface},
                headerTintColor:theme.colors.textPrimary,
                headerTitleStyle:{fontWeight:"700"} }}/>
            <Stack.Screen name="QuoteApproval" component={QuoteApprovalScreen}
              options={{ headerShown:true, title:"Repair Quote",
                headerStyle:{backgroundColor:theme.colors.surface},
                headerTintColor:theme.colors.textPrimary,
                headerTitleStyle:{fontWeight:"700"} }}/>
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
