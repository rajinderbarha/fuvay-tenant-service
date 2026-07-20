import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { HomeScreen }          from "../../screens/HomeScreen";
import { JobsListScreen }      from "../../screens/JobsListScreen";
import { ScheduleScreen }      from "../../screens/ux05/ScheduleScreen";
import { NotificationsScreen } from "../../screens/NotificationsScreen";
import { ProfileScreen }       from "../../screens/ProfileScreen";
import { theme } from "../../styles/theme";

/**
 * Technician bottom nav (workstream 2): Home / My Work / Schedule /
 * Notifications / Profile -- 5 items, matching the brief exactly. Extends
 * the pre-existing TabNavigator's icon/tab-bar styling rather than
 * reinventing it; only the tab SET differs (Notifications becomes a tab
 * instead of a stack-only bell-icon destination; Chat/Earnings move out --
 * Chat remains reachable from Job Detail/notifications deep-links, Earnings
 * is a known open gap per MODULE-L5-33 and was not promoted to a primary
 * tab in this redesign).
 */
const Tab = createBottomTabNavigator();

type TabIconProps = { label:string; icon:string; focused:boolean };
function TabIcon({ label, icon, focused }: TabIconProps) {
  return (
    <View style={s.iconWrap}>
      <Text style={[s.icon, focused && s.iconActive]}>{icon}</Text>
      <Text style={[s.label, focused && s.labelActive]}>{label}</Text>
    </View>
  );
}

export function TechnicianTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true, tabBarShowLabel: false, tabBarStyle: s.tabBar,
        headerStyle: { backgroundColor:theme.colors.surface },
        headerTintColor: theme.colors.textPrimary,
        headerTitleStyle: { fontWeight:"700", fontSize:theme.font.size.lg },
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen}
        options={{ title:"Home", tabBarIcon:({ focused }) => <TabIcon label="Home" icon="🏠" focused={focused}/> }}/>
      <Tab.Screen name="MyWork" component={JobsListScreen}
        options={{ title:"My Work", tabBarIcon:({ focused }) => <TabIcon label="My Work" icon="📋" focused={focused}/> }}/>
      <Tab.Screen name="Schedule" component={ScheduleScreen}
        options={{ title:"Schedule", tabBarIcon:({ focused }) => <TabIcon label="Schedule" icon="🗓" focused={focused}/> }}/>
      <Tab.Screen name="NotificationsTab" component={NotificationsScreen}
        options={{ title:"Notifications", tabBarIcon:({ focused }) => <TabIcon label="Alerts" icon="🔔" focused={focused}/> }}/>
      <Tab.Screen name="Profile" component={ProfileScreen}
        options={{ title:"Profile", tabBarIcon:({ focused }) => <TabIcon label="Profile" icon="👤" focused={focused}/> }}/>
    </Tab.Navigator>
  );
}

const s = StyleSheet.create({
  tabBar:      { backgroundColor:theme.colors.tabBg, borderTopWidth:1, borderTopColor:theme.colors.border,
                 height:64, paddingBottom:8 },
  iconWrap:    { alignItems:"center", gap:2, paddingTop:6 },
  icon:        { fontSize:22, opacity:0.45 },
  iconActive:  { opacity:1 },
  label:       { fontSize:9, fontWeight:"600", color:theme.colors.tabInactive },
  labelActive: { color:theme.colors.tabActive },
});
