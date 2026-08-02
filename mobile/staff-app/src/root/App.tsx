import React from "react";
import { StatusBar } from "expo-status-bar";
import { QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer } from "@react-navigation/native";
import { ThemeProvider, useTheme } from "../design-system/themes";
import { queryClient } from "./queryClient";
import { ComponentGallery } from "../design-system/gallery/ComponentGallery";
import { ErrorBoundary } from "./ErrorBoundary";
import { SessionProvider } from "../navigation/session/SessionProvider";
import { RootNavigator } from "../navigation/RootNavigator";
import { DeepLinkHandler } from "../navigation/DeepLinkHandler";
import { navigationRef } from "../navigation/navigationRef";

/**
 * Dev-only component gallery switch (Phase D). __DEV__ is Metro/Expo's
 * standard dev-vs-release flag. Set to true locally to QA the component
 * library in isolation; the shipped default is the real navigation shell.
 */
const SHOW_COMPONENT_GALLERY = false;

/**
 * Root provider order (Phase E spec section 12): ErrorBoundary is
 * outermost since it must survive a crash anywhere below it. QueryClient
 * and Theme come next (session invalidation needs the query client;
 * navigation UI needs theme tokens). SafeAreaProvider wraps navigation
 * since headers/tab bars are safe-area aware. SessionProvider resolves
 * the bootstrap/access state that NavigationContainer + RootNavigator
 * render from. DeepLinkHandler is mounted inside NavigationContainer so
 * it can use navigationRef once the container is ready.
 */
function ThemedStatusBar() {
  const { mode } = useTheme();
  return <StatusBar style={mode === "dark" ? "light" : "dark"} />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <SafeAreaProvider>
            <ThemedStatusBar />
            {SHOW_COMPONENT_GALLERY ? (
              <ComponentGallery />
            ) : (
              <SessionProvider>
                <NavigationContainer ref={navigationRef}>
                  <DeepLinkHandler />
                  <RootNavigator />
                </NavigationContainer>
              </SessionProvider>
            )}
          </SafeAreaProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
