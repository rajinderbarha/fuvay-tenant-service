import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { BaselineLandingScreen } from "../features/system/screens/BaselineLandingScreen";
import { DesignSystemShowcaseScreen } from "../design-system/showcase/DesignSystemShowcaseScreen";
import { StartupInspectorScreen } from "../features/system/screens/StartupInspectorScreen";
import { AppNavigator as LegacyAppNavigator } from "./AppNavigator";
import { ProfileScreen } from "../features/auth/screens/ProfileScreen";
import { SessionsScreen } from "../features/auth/screens/SessionsScreen";
import { OtpLoginScreen } from "../features/auth/screens/OtpLoginScreen";
import { HomeScreen } from "../features/home/screens/HomeScreen";
import { CategoryDetailScreen } from "../features/category/screens/CategoryDetailScreen";
import { ServiceDetailScreen } from "../features/service-detail/screens/ServiceDetailScreen";
import { SearchScreen } from "../features/search/screens/SearchScreen";
import { BookingAssistantScreen } from "../features/booking-assistant/screens/BookingAssistantScreen";
import { BookingDraftScreen } from "../features/booking-draft/screens/BookingDraftScreen";
import { BookingMediaScreen } from "../features/booking-draft/screens/BookingMediaScreen";
import { AddressListScreen } from "../features/address/screens/AddressListScreen";
import { AddressFormScreen } from "../features/address/screens/AddressFormScreen";
import { ServiceabilityScreen } from "../features/booking-draft/screens/ServiceabilityScreen";
import { ProviderPreviewScreen } from "../features/provider-matching/screens/ProviderPreviewScreen";
import { PricingEstimateScreen } from "../features/pricing/screens/PricingEstimateScreen";
import { BargainScreen } from "../features/bargain/screens/BargainScreen";
import { BookingReviewScreen } from "../features/booking-confirmation/screens/BookingReviewScreen";
import { BookingConfirmationScreen } from "../features/booking-confirmation/screens/BookingConfirmationScreen";
import { BookingsListScreen } from "../features/bookings/screens/BookingsListScreen";
import { BookingDetailScreen } from "../features/bookings/screens/BookingDetailScreen";
import { ServiceTrackingScreen } from "../features/service-tracking/screens/ServiceTrackingScreen";
import { QuoteDecisionScreen } from "../features/quote-decision/screens/QuoteDecisionScreen";

const Stack = createNativeStackNavigator();

/**
 * The app's reachable-once-startup-succeeds area. `Home` (CUSTOMER-L5-03)
 * is now the real production landing screen for authenticated customers —
 * `BaselineLanding` remains mounted as the guest/system-baseline screen
 * (see startup-route-resolver.ts's auth-based default-landing choice).
 * `LegacyApp` nests the pre-existing CUSTOMER-L5-00-and-earlier
 * authenticated app stack so its login flow and 19 screens stay reachable.
 * Dev-only routes are excluded from production via `__DEV__`.
 */
export interface MainNavigatorProps {
  initialRouteName?: "BaselineLanding" | "Home";
}

export function MainNavigator({ initialRouteName = "BaselineLanding" }: MainNavigatorProps) {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName={initialRouteName}>
      <Stack.Screen name="BaselineLanding" component={BaselineLandingScreen} />
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="CategoryDetail" component={CategoryDetailScreen} />
      <Stack.Screen name="ServiceDetails" component={ServiceDetailScreen} />
      <Stack.Screen name="Search" component={SearchScreen} />
      <Stack.Screen name="BookingAssistant" component={BookingAssistantScreen} />
      <Stack.Screen name="BookingDraft" component={BookingDraftScreen} />
      <Stack.Screen name="BookingMedia" component={BookingMediaScreen} />
      <Stack.Screen name="AddressSelection" component={AddressListScreen} />
      <Stack.Screen name="AddressForm" component={AddressFormScreen} />
      <Stack.Screen name="ServiceabilityCheck" component={ServiceabilityScreen} />
      <Stack.Screen name="ProviderPreview" component={ProviderPreviewScreen} />
      <Stack.Screen name="Pricing" component={PricingEstimateScreen} />
      <Stack.Screen name="Bargain" component={BargainScreen} />
      <Stack.Screen name="BookingReview" component={BookingReviewScreen} />
      <Stack.Screen name="BookingSuccess" component={BookingConfirmationScreen} />
      <Stack.Screen name="BookingsList" component={BookingsListScreen} />
      <Stack.Screen name="BookingDetail" component={BookingDetailScreen} />
      <Stack.Screen name="Tracking" component={ServiceTrackingScreen} />
      <Stack.Screen name="QuoteDecision" component={QuoteDecisionScreen} />
      <Stack.Screen name="Profile" component={ProfileScreen} options={{ headerShown: true, title: "Profile" }} />
      <Stack.Screen name="Sessions" component={SessionsScreen} options={{ headerShown: true, title: "Sessions and devices" }} />
      <Stack.Screen name="Authentication" component={OtpLoginScreen} options={{ headerShown: true, title: "Sign in" }} />
      <Stack.Screen name="LegacyApp" component={LegacyAppNavigator} />
      {__DEV__ ? (
        <>
          <Stack.Screen
            name="DesignSystemShowcase"
            component={DesignSystemShowcaseScreen}
            options={{ headerShown: true, title: "Design System Showcase (dev)" }}
          />
          <Stack.Screen name="StartupInspector" component={StartupInspectorScreen} options={{ headerShown: true, title: "Startup Inspector (dev)" }} />
        </>
      ) : null}
    </Stack.Navigator>
  );
}
