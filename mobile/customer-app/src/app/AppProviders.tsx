import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../design-system/themes/theme-provider";
import { queryClient } from "../state/query-client";
import { ErrorBoundary } from "./ErrorBoundary";
import { ToastHost } from "../components/feedback/ToastHost";

/**
 * Root providers only — no booking/marketplace business logic. Wraps the
 * existing app tree (AuthProvider/AppNavigator) without changing it.
 */
export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          {children}
          <ToastHost />
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
