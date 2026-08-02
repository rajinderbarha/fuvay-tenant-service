import React from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import { useFonts } from "expo-font";
import { Ionicons } from "@expo/vector-icons";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AppNavigator } from "./navigation/AppNavigator";

// UX-05 Round 5: ThemeProvider wraps the app so every screen/component that
// calls useAppTheme() reacts to the resolved light/dark scheme -- see
// context/ThemeContext.tsx. StatusBar's "auto" style already adapts to the
// OS scheme on its own (an Expo built-in), independent of this provider.
export default function App() {
  // Every tab-bar icon renders through Ionicons directly (see
  // navigation/ux05/{Technician,Staff}TabNavigator.tsx). Rendering before
  // the icon font asset has actually finished loading over the network
  // shows the raw glyph codepoint instead of the real icon -- which iOS
  // substitutes with its color-emoji font for several of the affected
  // codepoints. This gate blocks first render until the font is genuinely
  // ready, so that never happens (most visible over a slow/tunnel
  // connection, but a real bug regardless of transport).
  const [fontsLoaded] = useFonts({ ...Ionicons.font });

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#F7F6F3" }}>
        <ActivityIndicator size="large" color="#D9642B" />
      </View>
    );
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <AppNavigator />
      </AuthProvider>
    </ThemeProvider>
  );
}
