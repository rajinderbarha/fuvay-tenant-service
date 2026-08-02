import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { StaffHomeScreen }       from "../../screens/ux05/StaffHomeScreen";
import { StaffWorkQueueScreen }  from "../../screens/ux05/StaffWorkQueueScreen";
import { ScheduleScreen }        from "../../screens/ux05/ScheduleScreen";
import { NotificationsScreen }   from "../../screens/NotificationsScreen";
import { StaffMoreScreen }       from "../../screens/ux05/StaffMoreScreen";
import { theme } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";

/**
 * Staff bottom nav (workstream 2): Home / Work / Schedule / Notifications /
 * More -- 5 items. "More" exposes ONLY permission-compatible areas
 * (StaffMoreScreen renders each entry through PermissionRestrictedState
 * when the underlying StaffPermission isn't granted) -- never tenant-owner
 * administration, which this app has no route for at all.
 *
 * UX-05 Round 5: tab bar/header colors come from useAppTheme() (real,
 * tracked theme system).
 *
 * UX-05-TRACK-TAB-ICONS fix: see TechnicianTabNavigator.tsx -- these tabs
 * rendered raw emoji characters instead of a real icon glyph. Fixed with
 * Ionicons directly (self-contained -- no dependency on the untracked
 * design-system/ tree).
 */
const Tab = createBottomTabNavigator();

const TAB_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  StaffHome: "home-outline",
  WorkQueue: "briefcase-outline",
  Schedule: "calendar-outline",
  NotificationsTab: "notifications-outline",
  More: "ellipsis-horizontal-outline",
};

export function StaffTabNavigator() {
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
      <Tab.Screen name="StaffHome" component={StaffHomeScreen} options={{ title: "Home" }} />
      <Tab.Screen name="WorkQueue" component={StaffWorkQueueScreen} options={{ title: "Work" }} />
      <Tab.Screen name="Schedule" component={ScheduleScreen} options={{ title: "Schedule" }} />
      <Tab.Screen name="NotificationsTab" component={NotificationsScreen} options={{ title: "Notifications", tabBarLabel: "Alerts" }} />
      <Tab.Screen name="More" component={StaffMoreScreen} options={{ title: "More" }} />
    </Tab.Navigator>
  );
}
