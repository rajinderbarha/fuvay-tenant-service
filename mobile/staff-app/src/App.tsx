import React from "react";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AppNavigator } from "./navigation/AppNavigator";

// UX-05 Round 5: ThemeProvider wraps the app so every screen/component that
// calls useAppTheme() reacts to the resolved light/dark scheme -- see
// context/ThemeContext.tsx. StatusBar's "auto" style already adapts to the
// OS scheme on its own (an Expo built-in), independent of this provider.
export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <AppNavigator />
      </AuthProvider>
    </ThemeProvider>
  );
}
