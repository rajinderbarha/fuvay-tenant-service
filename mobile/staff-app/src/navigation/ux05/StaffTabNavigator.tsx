import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
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
 * UX-05 Round 5: tab bar/header colors now come from useAppTheme() (reactive
 * light/dark), not the static theme.colors import.
 */
const Tab = createBottomTabNavigator();

type TabIconProps = { label:string; icon:string; focused:boolean; colors:ReturnType<typeof import("../../styles/theme").getColors> };
function TabIcon({ label, icon, focused, colors }: TabIconProps) {
  return (
    <View style={s.iconWrap}>
      <Text style={[s.icon, focused && s.iconActive]}>{icon}</Text>
      <Text style={[s.label, { color: focused ? colors.tabActive : colors.tabInactive }]}>{label}</Text>
    </View>
  );
}

export function StaffTabNavigator() {
  const { colors } = useAppTheme();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true, tabBarShowLabel: false,
        tabBarStyle: { backgroundColor:colors.tabBg, borderTopWidth:1, borderTopColor:colors.border, height:64, paddingBottom:8 },
        headerStyle: { backgroundColor:colors.surface },
        headerTintColor: colors.textPrimary,
        headerTitleStyle: { fontWeight:"700", fontSize:theme.font.size.lg },
      }}
    >
      <Tab.Screen name="StaffHome" component={StaffHomeScreen}
        options={{ title:"Home", tabBarIcon:({ focused }) => <TabIcon label="Home" icon="🏠" focused={focused} colors={colors}/> }}/>
      <Tab.Screen name="WorkQueue" component={StaffWorkQueueScreen}
        options={{ title:"Work", tabBarIcon:({ focused }) => <TabIcon label="Work" icon="🗂" focused={focused} colors={colors}/> }}/>
      <Tab.Screen name="Schedule" component={ScheduleScreen}
        options={{ title:"Schedule", tabBarIcon:({ focused }) => <TabIcon label="Schedule" icon="🗓" focused={focused} colors={colors}/> }}/>
      <Tab.Screen name="NotificationsTab" component={NotificationsScreen}
        options={{ title:"Notifications", tabBarIcon:({ focused }) => <TabIcon label="Alerts" icon="🔔" focused={focused} colors={colors}/> }}/>
      <Tab.Screen name="More" component={StaffMoreScreen}
        options={{ title:"More", tabBarIcon:({ focused }) => <TabIcon label="More" icon="⋯" focused={focused} colors={colors}/> }}/>
    </Tab.Navigator>
  );
}

const s = StyleSheet.create({
  iconWrap:    { alignItems:"center", gap:2, paddingTop:6 },
  icon:        { fontSize:22, opacity:0.45 },
  iconActive:  { opacity:1 },
  label:       { fontSize:9, fontWeight:"600" },
});
