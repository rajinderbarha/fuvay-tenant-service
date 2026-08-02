import React, { useCallback } from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { AppTabsParamList } from "./routeTypes";
import { Icon, IconProps } from "../design-system/components/Icon";
import { useTheme } from "../design-system/themes";
import { useTabBadge, defaultBadgeAdapter } from "./placeholders/badges";
import { TechnicianHomeScreen } from "../screens/home/TechnicianHomeScreen";
import { JobsScreen } from "../screens/jobs/JobsScreen";
import { ScheduleNavigator } from "./ScheduleNavigator";
import { NotificationsScreen } from "../screens/notifications/NotificationsScreen";
import { ProfileNavigator } from "./ProfileNavigator";

const Tab = createBottomTabNavigator<AppTabsParamList>();

const TAB_ICON: Record<keyof AppTabsParamList, IconProps["name"]> = {
  Home: "home-outline",
  Jobs: "briefcase-outline",
  Schedule: "calendar-outline",
  Notifications: "notifications-outline",
  Profile: "person-outline",
};

/**
 * The five primary tabs (spec sections 1, 6). Tab order/names are stable
 * and never reordered by permission -- there is currently no tab a
 * technician/staff identity can't see, so no hide-policy branch exists yet;
 * if one is needed later it belongs here, centrally, not scattered in
 * individual screens.
 */
export function AppTabs() {
  const { theme } = useTheme();
  const jobsBadgeFetcher = useCallback(() => defaultBadgeAdapter.fetchActionableJobCount(), []);
  const notificationsBadgeFetcher = useCallback(() => defaultBadgeAdapter.fetchUnreadNotificationCount(), []);
  const jobsBadge = useTabBadge(jobsBadgeFetcher);
  const notificationsBadge = useTabBadge(notificationsBadgeFetcher);

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.brandPrimary,
        tabBarInactiveTintColor: theme.colors.textTertiary,
        // Match the customer app's bottom tab bar: an elevated surface
        // distinct from the page background (customer uses a dedicated
        // "bottomNavigation" token; staff-app's equivalent elevated surface
        // is backgroundElevated -- same visual effect, no new token needed).
        tabBarStyle: {
          backgroundColor: theme.colors.backgroundElevated,
          borderTopColor: theme.colors.borderSubtle,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontSize: 11 },
        tabBarIcon: ({ color, focused }) => (
          <Icon name={TAB_ICON[route.name as keyof AppTabsParamList]} color={color} size="standard" decorative />
        ),
        tabBarAccessibilityLabel: route.name,
        tabBarHideOnKeyboard: true,
      })}
    >
      <Tab.Screen name="Home" component={TechnicianHomeScreen} />
      <Tab.Screen name="Jobs" component={JobsScreen} options={{ tabBarBadge: jobsBadge }} />
      <Tab.Screen name="Schedule" component={ScheduleNavigator} />
      <Tab.Screen name="Notifications" component={NotificationsScreen} options={{ tabBarBadge: notificationsBadge }} />
      <Tab.Screen name="Profile" component={ProfileNavigator} />
    </Tab.Navigator>
  );
}
