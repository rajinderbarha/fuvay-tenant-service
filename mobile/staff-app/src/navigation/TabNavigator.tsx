import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { HomeScreen }     from "../screens/HomeScreen";
import { JobsListScreen } from "../screens/JobsListScreen";
import { ChatListScreen } from "../screens/ChatListScreen";
import { EarningsScreen } from "../screens/EarningsScreen";
import { ProfileScreen }  from "../screens/ProfileScreen";
import { theme }          from "../styles/theme";

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

export function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown:     true,
        tabBarShowLabel: false,
        tabBarStyle:     s.tabBar,
        headerStyle:     { backgroundColor:theme.colors.surface },
        headerTintColor: theme.colors.textPrimary,
        headerTitleStyle:{ fontWeight:"700", fontSize:theme.font.size.lg },
      }}
    >
      <Tab.Screen name="Home"     component={HomeScreen}
        options={{ title:"Home", tabBarIcon:({ focused }) => <TabIcon label="Home"    icon="🏠" focused={focused}/> }}/>
      <Tab.Screen name="Jobs"     component={JobsListScreen}
        options={{ title:"My Jobs", tabBarIcon:({ focused }) => <TabIcon label="Jobs"    icon="📋" focused={focused}/> }}/>
      <Tab.Screen name="Chat"     component={ChatListScreen}
        options={{ title:"Chat",    tabBarIcon:({ focused }) => <TabIcon label="Chat"    icon="💬" focused={focused}/> }}/>
      <Tab.Screen name="Earnings" component={EarningsScreen}
        options={{ title:"Earnings",tabBarIcon:({ focused }) => <TabIcon label="Earnings"icon="💰" focused={focused}/> }}/>
      <Tab.Screen name="Profile"  component={ProfileScreen}
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
