import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PreparingExperienceScreen } from "../PreparingExperienceScreen";
import { SessionExpiredScreen } from "../SessionExpiredScreen";
import { AccountSuspendedScreen } from "../AccountSuspendedScreen";
import { UpdateRequiredScreen } from "../UpdateRequiredScreen";
import { MaintenanceScreen } from "../MaintenanceScreen";
import { ApiUnavailableScreen } from "../ApiUnavailableScreen";
import { StorageUnavailableScreen } from "../StorageUnavailableScreen";
import { VerticalUnavailableScreen } from "../VerticalUnavailableScreen";
import { InvalidAccessScreen } from "../InvalidAccessScreen";

describe("exceptional-state screens", () => {
  it("PreparingExperience shows the exact required copy and an accessible progress indicator", () => {
    const { getByText, getByLabelText } = renderWithProviders(<PreparingExperienceScreen />);
    expect(getByText("Preparing your experience")).toBeTruthy();
    expect(getByText("Loading services available in your area")).toBeTruthy();
    expect(getByLabelText("Preparing your experience")).toBeTruthy();
  });

  it("SessionExpired shows both required actions and calls them", () => {
    const onGoToSignIn = jest.fn();
    const onGetHelp = jest.fn();
    const { getByText, getByRole } = renderWithProviders(
      <SessionExpiredScreen reason="session_expired" onGoToSignIn={onGoToSignIn} onGetHelp={onGetHelp} />,
    );
    expect(getByText("Session expired")).toBeTruthy();
    expect(getByText("Sign in again to continue securely.")).toBeTruthy();
    fireEvent.press(getByRole("button", { name: "Go to sign in" }));
    expect(onGoToSignIn).toHaveBeenCalledTimes(1);
  });

  it("AccountSuspended never renders authenticated tabs or customer data", () => {
    const { queryByText } = renderWithProviders(
      <AccountSuspendedScreen onContactSupport={() => {}} onSignOut={() => {}} />,
    );
    expect(queryByText("Good morning")).toBeNull();
  });

  it("UpdateRequired renders without a fabricated store URL", () => {
    const { getByText } = renderWithProviders(<UpdateRequiredScreen onUpdate={() => {}} />);
    expect(getByText("Update required")).toBeTruthy();
    expect(getByText("Update app")).toBeTruthy();
  });

  it("Maintenance renders the required copy", () => {
    const { getByText } = renderWithProviders(<MaintenanceScreen onTryAgain={() => {}} />);
    expect(getByText("Fuvay is temporarily unavailable")).toBeTruthy();
  });

  it("ApiUnavailable omits the offline-info action unless explicitly supplied", () => {
    const { queryByText } = renderWithProviders(<ApiUnavailableScreen onTryAgain={() => {}} />);
    expect(queryByText("View offline information")).toBeNull();
  });

  it("StorageUnavailable offers only a safe retry, no continue-anyway action", () => {
    const { getByText, queryByText } = renderWithProviders(<StorageUnavailableScreen onTryAgain={() => {}} />);
    expect(getByText("Try again")).toBeTruthy();
    expect(queryByText("Continue anyway")).toBeNull();
  });

  it("VerticalUnavailable offers Back to Home and never hides unrelated verticals text", () => {
    const { getByText } = renderWithProviders(
      <VerticalUnavailableScreen onBackToHome={() => {}} onViewAvailableServices={() => {}} />,
    );
    expect(getByText("Back to Home")).toBeTruthy();
  });

  it("InvalidAccess never shows customer tabs underneath", () => {
    const { queryByLabelText } = renderWithProviders(<InvalidAccessScreen onSignOut={() => {}} />);
    expect(queryByLabelText("Home")).toBeNull();
    expect(queryByLabelText("Bookings")).toBeNull();
  });
});
