import React from "react";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "./context/AuthContext";
import { RootNavigator } from "./navigation/RootNavigator";
import { AppProviders } from "./app/AppProviders";
import { useAppBootstrap } from "./app/AppBootstrap";
import { StartupProvider } from "./app/startup/startup-context";
import { LoadingIndicator } from "./components/feedback/LoadingIndicator";

function AppContent() {
  const { isReady } = useAppBootstrap();

  if (!isReady) return <LoadingIndicator variant="screen" label="Starting ServiceOS" />;

  return (
    <StartupProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <RootNavigator />
      </AuthProvider>
    </StartupProvider>
  );
}

export default function App() {
  return (
    <AppProviders>
      <AppContent />
    </AppProviders>
  );
}
