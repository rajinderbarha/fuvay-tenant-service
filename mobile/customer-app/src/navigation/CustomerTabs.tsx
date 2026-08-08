import React, { useEffect, useRef, useState } from "react";
import { Animated, Easing, View, AccessibilityInfo } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { CommonActions } from "@react-navigation/native";
import { CustomerTabsParamList, CustomerTabName } from "./routeTypes";
import { Icon, IconProps } from "../components/Icon";
import { useTheme } from "../design-system/theme";
import { HomeScreen } from "../screens/home/HomeScreen";
import { MyBookingsScreen } from "../screens/bookings/MyBookingsScreen";
import { BookingChatScreen } from "../screens/bookingChat/BookingChatScreen";
import { HelpSupportScreen } from "../screens/support/HelpSupportScreen";
import { ProfileScreen } from "../screens/profile/ProfileScreen";
import { saveLastSelectedTab } from "./navigationPersistence";

const Tab = createBottomTabNavigator<CustomerTabsParamList>();

const TAB_ICON: Record<Exclude<CustomerTabName, "Assistant">, IconProps["name"]> = {
  Home: "home-outline",
  Bookings: "calendar-outline",
  Support: "headset-outline",
  Profile: "person-outline",
};

/** Assistant tab's central elevated circular treatment -- restored per
 * this task's explicit requirement (Level 5 Home spec section 10:
 * "Assistant uses the refined elevated orange sparkle action from the
 * approved design"). A gentle, continuous breathing pulse (scale +
 * shadow-opacity) draws the eye to it as the entry point into the
 * chatbot, without ever affecting layout or other tabs. Reduced-motion
 * users get the plain, static circle. */
function AssistantTabIcon({ focused }: { focused: boolean }) {
  const { theme } = useTheme();
  const pulse = useRef(new Animated.Value(0)).current;
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion).catch(() => {});
  }, []);

  useEffect(() => {
    if (reducedMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reducedMotion, pulse]);

  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] });

  return (
    <Animated.View
      style={{
        width: 44, height: 44, borderRadius: theme.radius.radiusFull,
        backgroundColor: focused ? theme.colors.brandPrimaryPressed : theme.colors.brandPrimary,
        alignItems: "center", justifyContent: "center", marginTop: -16,
        transform: reducedMotion ? undefined : [{ scale }],
        ...theme.shadow.md,
      }}
    >
      <Icon name="sparkles" size="standard" color={theme.colors.brandOnPrimary} decorative />
    </Animated.View>
  );
}

/** Five customer tabs, exact required order: Home, Bookings, Assistant,
 * Support, Profile. No Chat/Offers/Wallet/Payments/Providers tabs. */
export function CustomerTabs() {
  const { theme } = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.brandPrimary,
        tabBarInactiveTintColor: theme.colors.iconDefault,
        tabBarStyle: {
          backgroundColor: theme.colors.bottomNavigation,
          borderTopColor: theme.colors.borderSubtle,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontSize: 11 },
        tabBarAccessibilityLabel: route.name,
        tabBarHideOnKeyboard: true,
      })}
      screenListeners={{
        state: e => {
          const state = e.data.state;
          const activeRoute = state?.routes[state.index]?.name as CustomerTabName | undefined;
          if (activeRoute) saveLastSelectedTab(activeRoute);
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{ tabBarIcon: ({ color }) => <Icon name={TAB_ICON.Home} color={color} size="standard" decorative /> }}
      />
      <Tab.Screen
        name="Bookings"
        component={MyBookingsScreen}
        options={{ tabBarIcon: ({ color }) => <Icon name={TAB_ICON.Bookings} color={color} size="standard" decorative /> }}
      />
      {/* A tab keeps the params it was last navigated with. So once a customer
          had entered the Assistant from a service card on Home, every later tap
          on the tab itself re-entered with that category still attached -- the
          assistant opened straight into AC questions for someone who had asked
          for nothing. Entering from the tab is a category-less start, so the
          stale params are cleared (merge: false replaces them outright).

          Only when the tab is NOT already focused: tapping the tab you are
          standing on must not discard a conversation in progress. */}
      <Tab.Screen
        name="Assistant"
        component={BookingChatScreen}
        options={{ tabBarIcon: ({ focused }) => <AssistantTabIcon focused={focused} /> }}
        listeners={({ navigation }) => ({
          tabPress: () => {
            if (navigation.isFocused()) return;
            navigation.dispatch(
              CommonActions.navigate({ name: "Assistant", params: undefined, merge: false }),
            );
          },
        })}
      />
      <Tab.Screen
        name="Support"
        component={HelpSupportScreen}
        options={{ tabBarIcon: ({ color }) => <Icon name={TAB_ICON.Support} color={color} size="standard" decorative /> }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarIcon: ({ color }) => <Icon name={TAB_ICON.Profile} color={color} size="standard" decorative /> }}
      />
    </Tab.Navigator>
  );
}
