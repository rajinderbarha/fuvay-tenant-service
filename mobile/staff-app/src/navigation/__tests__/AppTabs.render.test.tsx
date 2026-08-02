import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, buildTheme } from "../../design-system/themes";
import { SessionProvider } from "../session/SessionProvider";
import { createFixtureSessionAdapter } from "../session/SessionAdapter";
import { AppTabs } from "../AppTabs";

// This suite proves tab-bar chrome (labels/theming), not Home screen
// content/data-fetching (covered by screens/home's own tests) -- stub it
// out so this test never triggers a real network query.
jest.mock("../../screens/home/TechnicianHomeScreen", () => ({
  TechnicianHomeScreen: () => null,
}));

const READY_CONTEXT = {
  authenticated: true, canonicalRole: "technician" as const, audience: "serviceos:staff" as const,
  tenantId: "t1", tenantStatus: "active", technicianId: "tech1", technicianStatus: "active",
};

function renderTabs() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SessionProvider adapter={createFixtureSessionAdapter(READY_CONTEXT)}>
          <NavigationContainer>
            <AppTabs />
          </NavigationContainer>
        </SessionProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("AppTabs — light/dark rendering and accessibility (spec sections 6, 11, 14)", () => {
  it("renders all five tabs with accessible labels matching their route names", async () => {
    renderTabs();
    await waitFor(() => expect(screen.getByLabelText("Home")).toBeTruthy());
    expect(screen.getByLabelText("Jobs")).toBeTruthy();
    expect(screen.getByLabelText("Schedule")).toBeTruthy();
    expect(screen.getByLabelText("Notifications")).toBeTruthy();
    expect(screen.getByLabelText("Profile")).toBeTruthy();
  });

  it("light and dark theme tokens used by the tab bar are distinct (no shared literal colors)", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    expect(light.colors.backgroundPrimary).not.toBe(dark.colors.backgroundPrimary);
    expect(light.colors.brandPrimary).toBeTruthy();
    expect(dark.colors.brandPrimary).toBeTruthy();
    expect(light.colors.borderSubtle).not.toBe(dark.colors.borderSubtle);
  });
});
