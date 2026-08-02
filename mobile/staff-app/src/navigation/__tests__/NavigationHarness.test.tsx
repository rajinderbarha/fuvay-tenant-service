import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "../../design-system/themes";
import { SessionProvider } from "../session/SessionProvider";
import { createFixtureSessionAdapter } from "../session/SessionAdapter";
import { RootNavigator } from "../RootNavigator";
import { AccessContext, UNAUTHENTICATED_CONTEXT } from "../guards/types";

/**
 * Integration harness (spec section 14): renders the real navigation tree
 * end-to-end and switches which screen is reachable purely by swapping the
 * injected fixture access context -- no Login screen/API is implemented or
 * needed to prove every access state routes correctly.
 */
function renderWithAccessContext(accessContext: AccessContext) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SafeAreaProvider initialMetrics={{ frame: { x: 0, y: 0, width: 390, height: 844 }, insets: { top: 0, left: 0, right: 0, bottom: 0 } }}>
          <SessionProvider adapter={createFixtureSessionAdapter(accessContext)}>
            <NavigationContainer>
              <RootNavigator />
            </NavigationContainer>
          </SessionProvider>
        </SafeAreaProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

const READY_CONTEXT: AccessContext = {
  authenticated: true, canonicalRole: "technician", audience: "serviceos:staff",
  tenantId: "t1", tenantStatus: "active", technicianId: "tech1", technicianStatus: "active",
};

describe("Navigation harness — fixture access states route to the correct tree", () => {
  it("unauthenticated fixture reaches the AuthStack Login screen", async () => {
    renderWithAccessContext(UNAUTHENTICATED_CONTEXT);
    await waitFor(() => expect(screen.getByText("Welcome back")).toBeTruthy());
  });

  it("authenticated_ready fixture reaches AppTabs (Home visible, all five tabs present)", async () => {
    renderWithAccessContext(READY_CONTEXT);
    await waitFor(() => expect(screen.getAllByText("Home").length).toBeGreaterThan(0));
    expect(screen.getByLabelText("Home")).toBeTruthy();
    expect(screen.getByLabelText("Jobs")).toBeTruthy();
    expect(screen.getByLabelText("Schedule")).toBeTruthy();
    expect(screen.getByLabelText("Notifications")).toBeTruthy();
    expect(screen.getByLabelText("Profile")).toBeTruthy();
  });

  it("account_suspended fixture reaches the restricted AccountSuspended screen, not AppTabs", async () => {
    renderWithAccessContext({ ...READY_CONTEXT, technicianStatus: "suspended" });
    await waitFor(() => expect(screen.getByText("Work access suspended")).toBeTruthy());
    expect(screen.queryByLabelText("Jobs")).toBeNull();
  });

  it("tenant_suspended fixture reaches the restricted TenantSuspended screen", async () => {
    renderWithAccessContext({ ...READY_CONTEXT, tenantStatus: "suspended" });
    await waitFor(() => expect(screen.getByText("Work access suspended")).toBeTruthy());
  });

  it("wrong-audience fixture reaches AccessDenied, never AppTabs", async () => {
    renderWithAccessContext({ ...READY_CONTEXT, audience: "serviceos:customer" });
    await waitFor(() => expect(screen.getByText("Access denied")).toBeTruthy());
    expect(screen.queryByLabelText("Home")).toBeNull();
  });

  it("missing technician context reaches AccessDenied, not a crash or blank screen", async () => {
    renderWithAccessContext({ ...READY_CONTEXT, technicianId: undefined });
    await waitFor(() => expect(screen.getByText("Access denied")).toBeTruthy());
  });
});
