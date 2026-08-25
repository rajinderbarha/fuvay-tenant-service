import React, { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Dimensions } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { ThemeProvider, useTheme } from "../design-system/theme";
import { queryClient } from "../api/queryClient";
import { startNetworkMonitoring, stopNetworkMonitoring } from "../api/networkState";
import { ErrorBoundary } from "../root/ErrorBoundary";
import { AuthProvider } from "../auth/AuthContext";
import { ServiceLocationProvider } from "../hooks/useServiceLocationPreference";

function ThemedStatusBar() {
  const { mode } = useTheme();
  return <StatusBar style={mode === "dark" ? "light" : "dark"} />;
}

function NetworkMonitor() {
  useEffect(() => {
    startNetworkMonitoring();
    return () => stopNetworkMonitoring();
  }, []);
  return null;
}

/**
 * Root provider composition. Order: ErrorBoundary is outermost since it
 * must survive a crash anywhere below it. QueryClient and Theme come next.
 * SafeAreaProvider wraps everything content-facing since screens are
 * safe-area aware. AuthProvider resolves the (currently foundation-only)
 * session state that a future navigation shell will branch on.
 */
// Seeds SafeAreaProvider with a best-guess frame before its first native
// measurement lands -- under react-test-renderer that measurement never
// happens at all, so without this children would never render in tests.
const { width, height } = Dimensions.get("window");
const INITIAL_SAFE_AREA_METRICS = {
  frame: { x: 0, y: 0, width: width || 390, height: height || 844 },
  insets: { top: 0, left: 0, right: 0, bottom: 0 },
};

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <SafeAreaProvider initialMetrics={INITIAL_SAFE_AREA_METRICS}>
            <ThemedStatusBar />
            <NetworkMonitor />
            <ServiceLocationProvider>
              <AuthProvider>{children}</AuthProvider>
            </ServiceLocationProvider>
          </SafeAreaProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
