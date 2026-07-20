import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StaffHomeScreen }       from "../../screens/ux05/StaffHomeScreen";
import { StaffWorkQueueScreen }  from "../../screens/ux05/StaffWorkQueueScreen";
import { ScheduleScreen }        from "../../screens/ux05/ScheduleScreen";
import { NotificationsScreen }   from "../../screens/NotificationsScreen";
import { StaffMoreScreen }       from "../../screens/ux05/StaffMoreScreen";
import { theme } from "../../styles/theme";

/**
 * Staff bottom nav (workstream 2): Home / Work / Schedule / Notifications /
 * More -- 5 items. "More" exposes ONLY permission-compatible areas
 * (StaffMoreScreen renders each entry through PermissionRestrictedState
 * when the underlying StaffPermission isn't granted) -- never tenant-owner
 * administration, which this app has no route for at all.
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

export function StaffTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true, tabBarShowLabel: false, tabBarStyle: s.tabBar,
        headerStyle: { backgroundColor:theme.colors.surface },
        headerTintColor: theme.colors.textPrimary,
        headerTitleStyle: { fontWeight:"700", fontSize:theme.font.size.lg },
      }}
    >
      <Tab.Screen name="StaffHome" component={StaffHomeScreen}
        options={{ title:"Home", tabBarIcon:({ focused }) => <TabIcon label="Home" icon="🏠" focused={focused}/> }}/>
      <Tab.Screen name="WorkQueue" component={StaffWorkQueueScreen}
        options={{ title:"Work", tabBarIcon:({ focused }) => <TabIcon label="Work" icon="🗂" focused={focused}/> }}/>
      <Tab.Screen name="Schedule" component={ScheduleScreen}
        options={{ title:"Schedule", tabBarIcon:({ focused }) => <TabIcon label="Schedule" icon="🗓" focused={focused}/> }}/>
      <Tab.Screen name="NotificationsTab" component={NotificationsScreen}
        options={{ title:"Notifications", tabBarIcon:({ focused }) => <TabIcon label="Alerts" icon="🔔" focused={focused}/> }}/>
      <Tab.Screen name="More" component={StaffMoreScreen}
        options={{ title:"More", tabBarIcon:({ focused }) => <TabIcon label="More" icon="⋯" focused={focused}/> }}/>
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
