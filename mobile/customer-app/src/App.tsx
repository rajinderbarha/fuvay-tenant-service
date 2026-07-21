import React from "react";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AppNavigator } from "./navigation/AppNavigator";

// UX-07 Round 4 Pass 2: ThemeProvider wraps everything so the resolved
// mode (System/Light/Dark) and persisted preference are available to the
// whole tree; AppNavigator now renders its own theme-aware <StatusBar/>
// once the persisted preference has loaded, avoiding a flash-of-wrong-theme.
export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppNavigator/>
      </AuthProvider>
    </ThemeProvider>
  );
}
