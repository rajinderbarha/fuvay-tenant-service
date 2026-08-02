import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { HomeScreen }          from "../../screens/HomeScreen";
import { JobsListScreen }      from "../../screens/JobsListScreen";
import { ScheduleScreen }      from "../../screens/ux05/ScheduleScreen";
import { NotificationsScreen } from "../../screens/NotificationsScreen";
import { ProfileScreen }       from "../../screens/ProfileScreen";
import { theme } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";

/**
 * Technician bottom nav (workstream 2): Home / My Work / Schedule /
 * Notifications / Profile -- 5 items, matching the brief exactly.
 *
 * UX-05 Round 5: tab bar/header colors come from useAppTheme() (this app's
 * real, tracked theme system -- reactive light/dark).
 *
 * UX-05-TRACK-TAB-ICONS fix: these five tabs previously rendered raw emoji
 * characters (🏠📋🗓🔔👤) as the "icon" -- on iOS that renders through the
 * system color-emoji font, which is why the tab bar looked like a row of
 * emoji instead of real icons. Fixed with Ionicons directly (self-contained
 * -- no dependency on the untracked design-system/ tree sitting alongside
 * this app; see git status before reaching for that folder again).
 */
const Tab = createBottomTabNavigator();

const TAB_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  Home: "home-outline",
  MyWork: "briefcase-outline",
  Schedule: "calendar-outline",
  NotificationsTab: "notifications-outline",
  Profile: "person-outline",
};

export function TechnicianTabNavigator() {
  const { colors } = useAppTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: true,
        tabBarActiveTintColor: colors.tabActive,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarStyle: { backgroundColor: colors.tabBg, borderTopWidth: 1, borderTopColor: colors.border },
        tabBarLabelStyle: { fontSize: theme.font.size.xs, fontWeight: theme.font.weight.semibold },
        tabBarIcon: ({ color }) => <Ionicons name={TAB_ICON[route.name]} size={22} color={color} />,
        tabBarAccessibilityLabel: route.name,
        tabBarHideOnKeyboard: true,
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.textPrimary,
        headerTitleStyle: { fontWeight: "700", fontSize: theme.font.size.lg },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: "Home" }} />
      <Tab.Screen name="MyWork" component={JobsListScreen} options={{ title: "My Work" }} />
      <Tab.Screen name="Schedule" component={ScheduleScreen} options={{ title: "Schedule" }} />
      <Tab.Screen name="NotificationsTab" component={NotificationsScreen} options={{ title: "Notifications", tabBarLabel: "Alerts" }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: "Profile" }} />
    </Tab.Navigator>
  );
}
