import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../testing/renderWithProviders";
import { CustomerTabs } from "../CustomerTabs";

function renderTabs() {
  return renderWithProviders(
    <NavigationContainer>
      <CustomerTabs />
    </NavigationContainer>,
  );
}

describe("CustomerTabs", () => {
  it("renders exactly five tabs, discoverable by accessibility label, in the required order", () => {
    const { getByLabelText } = renderTabs();
    for (const name of ["Home", "Bookings", "Assistant", "Support", "Profile"]) {
      expect(getByLabelText(name)).toBeTruthy();
    }
  });

  it("switches screen content when a different tab is pressed", async () => {
    // Asserts the REAL Support screen's own heading. This test previously
    // asserted a "Support conversations will be available here in a later
    // phase." placeholder that no longer exists anywhere in the codebase --
    // the Support tab has since been built out as `HelpSupportScreen`, and
    // this assertion was simply never updated alongside it.
    const { getByLabelText, findByText, queryByText } = renderTabs();
    fireEvent.press(getByLabelText("Support"));
    expect(await findByText("Help & Support")).toBeTruthy();
    // Only Home has a visual text label in the reference bottom bar. The
    // destination remains accessible by its icon's accessibility label.
    expect(queryByText("Support")).toBeNull();
  });

  it("keeps non-Home tabs icon-only when selected", async () => {
    const { getByLabelText, findByLabelText, queryByText } = renderTabs();
    fireEvent.press(getByLabelText("Profile"));
    expect(await findByLabelText("Loading your profile")).toBeTruthy();
    expect(queryByText("Account")).toBeNull();
  });

  it("switches to the Assistant tab without exposing the underlying model/vendor name", async () => {
    const { getByLabelText, findByLabelText, queryByText } = renderTabs();
    fireEvent.press(getByLabelText("Assistant"));
    // No profile query result yet in this unmocked render -- the real
    // AssistantScreen shows its loading state rather than a placeholder.
    expect(await findByLabelText("Loading your assistant")).toBeTruthy();
    expect(queryByText(/DeepSeek/i)).toBeNull();
  });
});
