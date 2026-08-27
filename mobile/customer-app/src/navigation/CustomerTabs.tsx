import React from "react";
import { Platform, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { CommonActions } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { CustomerTabsParamList, CustomerTabName } from "./routeTypes";
import { Icon, IconProps } from "../components/Icon";
import { useTheme } from "../design-system/theme";
import { HomeScreen } from "../screens/home/HomeScreen";
import { MyBookingsScreen } from "../screens/bookings/MyBookingsScreen";
import { BookingChatScreen } from "../screens/bookingChat/BookingChatScreen";
import { HelpSupportScreen } from "../screens/support/HelpSupportScreen";
import { ProfileScreen } from "../screens/profile/ProfileScreen";
import { saveLastSelectedTab } from "./navigationPersistence";
import { FuvayIcon } from "../components/FuvayIcon";

const Tab = createBottomTabNavigator<CustomerTabsParamList>();

const TAB_ICON: Record<Exclude<CustomerTabName, "Assistant">, IconProps["name"]> = {
  Home: "home-outline",
  Bookings: "calendar-outline",
  Support: "headset-outline",
  Profile: "person-outline",
};

function AssistantTabIcon({ focused }: { focused: boolean }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        width: 52, height: 52, borderRadius: 26,
        backgroundColor: "#FFFFFF",
        borderWidth: focused ? 3 : 2,
        borderColor: focused ? theme.colors.brandPrimary : theme.colors.borderStrong,
        alignItems: "center", justifyContent: "center", marginTop: -18,
        ...theme.shadow.md,
      }}
    >
      <FuvayIcon size={30} accessibilityLabel="Fuvay assistant" />
    </View>
  );
}

/** Five customer tabs, exact required order: Home, Bookings, Assistant,
 * Support, Profile. No Chat/Offers/Wallet/Payments/Providers tabs. */
export function CustomerTabs() {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  // Android edge-to-edge navigation can report zero briefly in Expo Go. Keep
  // a conservative floor so the centre label never sits under the system bar.
  const bottomInset = Math.max(insets.bottom, Platform.OS === "android" ? 16 : 8);

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.textPrimary,
        tabBarInactiveTintColor: theme.colors.iconDefault,
        tabBarStyle: {
          backgroundColor: theme.colors.bottomNavigation,
          borderColor: theme.colors.borderSubtle,
          borderWidth: 1,
          height: 66 + bottomInset,
          paddingTop: 8,
          paddingBottom: bottomInset,
          position: "absolute",
          left: 12,
          right: 12,
          bottom: 8,
          borderRadius: 28,
          overflow: "visible",
          ...theme.shadow.md,
        },
        tabBarItemStyle: { minHeight: 60, overflow: "visible" },
        tabBarLabelStyle: { fontSize: 10.5, lineHeight: 14, fontWeight: "600", marginTop: 1 },
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
        options={{
          tabBarLabel: "Ask Fuvay",
          tabBarIcon: ({ focused }) => <AssistantTabIcon focused={focused} />,
        }}
        listeners={({ navigation }) => ({
          tabPress: () => {
            if (navigation.isFocused()) return;
            navigation.dispatch(
              CommonActions.navigate("Assistant", undefined, { merge: false }),
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
