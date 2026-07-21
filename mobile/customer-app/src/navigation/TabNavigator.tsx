import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
// UX-06 Round 3 fix: HomeScreen.tsx uses `export default`, not a named export
// -- this was a pre-existing runtime-breaking bug (React Navigation received
// `undefined` for the Home tab's component), discovered via a real Playwright
// browser run against Expo web this round.
import HomeScreen              from "../screens/HomeScreen";
import { BookingsListScreen } from "../screens/BookingsListScreen";
import { DeepSeekChatScreen } from "../screens/DeepSeekChatScreen";
import { ChatScreen }         from "../screens/ChatScreen";
import { ProfileScreen }      from "../screens/ProfileScreen";
import { useTheme } from "../context/ThemeContext";

// UX-06 Round 5: real typed tab param list (HomeScreen/ProfileScreen declare
// NativeStackScreenProps<{Home:undefined}>/<{Profile:undefined}> themselves —
// this matches that, resolving the last Pattern F typecheck errors).
export type TabParamList = {
  Home: undefined;
  Bookings: undefined;
  AIAssistant: undefined;
  Chat: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<TabParamList>();

function TabIcon({ icon, label, focused }:{ icon:string; label:string; focused:boolean }) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems:"center", gap:2, paddingTop:6 }}
      accessible accessibilityLabel={`${label} tab${focused ? ", selected" : ""}`}>
      <Text style={{ fontSize:22, opacity:focused?1:0.45 }}>{icon}</Text>
      <Text style={{ fontSize:9, fontWeight:"600",
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
        options={{ title:"Home",    tabBarIcon:({focused})=><TabIcon icon="🏠" label="Home"    focused={focused}/> }}/>
      <Tab.Screen name="Bookings" component={BookingsListScreen}
        options={{ title:"My Bookings", tabBarIcon:({focused})=><TabIcon icon="📋" label="Bookings" focused={focused}/> }}/>
      {/* UX-06 Round 3: wired to the real, live-confirmed DeepSeek chat screen
          (see docs/design/ux-06-customer-app/deepseek-conversation-contract.md).
          The prior AIChatScreen was a legacy scaffold screen with no confirmed
          real backend contract behind it. */}
      <Tab.Screen name="AIAssistant" component={DeepSeekChatScreen}
        options={{ title:"AI Assistant", tabBarIcon:({focused})=><TabIcon icon="🤖" label="AI Chat"  focused={focused}/> }}/>
      <Tab.Screen name="Chat"     component={ChatScreen}
        options={{ title:"Messages", tabBarIcon:({focused})=><TabIcon icon="💬" label="Chat"    focused={focused}/> }}/>
      <Tab.Screen name="Profile"  component={ProfileScreen}
        options={{ title:"Profile", tabBarIcon:({focused})=><TabIcon icon="👤" label="Profile" focused={focused}/> }}/>
    </Tab.Navigator>
  );
}
