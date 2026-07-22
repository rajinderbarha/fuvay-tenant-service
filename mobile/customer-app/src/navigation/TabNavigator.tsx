import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
// UX-06 Round 3 fix: HomeScreen.tsx uses `export default`, not a named export
// -- this was a pre-existing runtime-breaking bug (React Navigation received
// `undefined` for the Home tab's component), discovered via a real Playwright
// browser run against Expo web this round.
import HomeScreen              from "../screens/HomeScreen";
import { BookingsListScreen } from "../screens/BookingsListScreen";
import { DeepSeekChatScreen } from "../screens/DeepSeekChatScreen";
import { NotificationsScreen } from "../screens/NotificationsScreen";
import { ProfileScreen }      from "../screens/ProfileScreen";
import { useTheme } from "../context/ThemeContext";

// UX-07 Pass 3d: bottom nav narrowed to exactly Home / Bookings / SmartBot /
// Notifications / Profile per this pass's brief. The standalone "Chat" tab
// (human/provider support chat, distinct from SmartBot -- see Pass 3b's
// disposition note still on ChatScreen.tsx) is NOT deleted: it is a real,
// distinct surface backed by a real chatApi contract, not a SmartBot
// duplicate. It is folded into Profile > Support > "Messages" instead (see
// ProfileScreen.tsx + AppNavigator's new root-stack "Chat" entry) so it
// remains reachable without occupying a primary tab slot. AIAssistant's
// route now accepts optional { initialCategoryLabel } params so Home's
// category tiles/search can hand off context without re-asking "what do you
// need" -- see DeepSeekChatScreen.tsx.
export type TabParamList = {
  Home: undefined;
  Bookings: undefined;
  AIAssistant: { initialCategoryLabel?: string } | undefined;
  Notifications: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<TabParamList>();

function TabIcon({ icon, label, focused }:{ icon:keyof typeof Ionicons.glyphMap; label:string; focused:boolean }) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems:"center", gap:2, paddingTop:6 }}
      accessible accessibilityRole="tab" accessibilityState={{ selected: focused }}
      accessibilityLabel={`${label} tab${focused ? ", selected" : ""}`}>
      <Ionicons name={icon} size={22} color={focused ? theme.colors.tabActive : theme.colors.tabInactive}/>
      <Text numberOfLines={1} style={{ fontSize:9, fontWeight:"600",
        color:focused?theme.colors.tabActive:theme.colors.tabInactive }}>{label}</Text>
    </View>
  );
}

export function TabNavigator() {
  const { theme } = useTheme();
  return (
    <Tab.Navigator screenOptions={{
      headerShown:true, tabBarShowLabel:false,
      tabBarStyle:{ backgroundColor:theme.colors.surface, borderTopWidth:1,
        borderTopColor:theme.colors.border, height:64, paddingBottom:8 },
      headerStyle:{ backgroundColor:theme.colors.surface },
      headerTintColor:theme.colors.textPrimary,
      headerTitleStyle:{ fontWeight:"700", fontSize:theme.font.size.lg },
    }}>
      <Tab.Screen name="Home"     component={HomeScreen}
        options={{ title:"Home",    tabBarIcon:({focused})=><TabIcon icon="home"        label="Home"    focused={focused}/> }}/>
      <Tab.Screen name="Bookings" component={BookingsListScreen}
        options={{ title:"My Bookings", tabBarIcon:({focused})=><TabIcon icon="calendar" label="Bookings" focused={focused}/> }}/>
      {/* UX-06 Round 3: wired to the real, live-confirmed DeepSeek chat screen
          (see docs/design/ux-06-customer-app/deepseek-conversation-contract.md).
          The prior AIChatScreen was a legacy scaffold screen with no confirmed
          real backend contract behind it. */}
      <Tab.Screen name="AIAssistant" component={DeepSeekChatScreen}
        options={{ title:"SmartBot", tabBarIcon:({focused})=><TabIcon icon="sparkles" label="SmartBot" focused={focused}/> }}/>
      <Tab.Screen name="Notifications" component={NotificationsScreen}
        options={{ title:"Notifications", tabBarIcon:({focused})=><TabIcon icon="notifications" label="Alerts" focused={focused}/> }}/>
      <Tab.Screen name="Profile"  component={ProfileScreen}
        options={{ title:"Profile", tabBarIcon:({focused})=><TabIcon icon="person" label="Profile" focused={focused}/> }}/>
    </Tab.Navigator>
  );
}
