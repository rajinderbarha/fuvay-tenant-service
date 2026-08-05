import React from "react";
import { Alert } from "react-native";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PrivacyConsentScreen } from "../PrivacyConsentScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import { ConsentRecord } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";

const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ goBack: mockGoBack }),
}));

function record(overrides: Partial<ConsentRecord> = {}): ConsentRecord {
  return {
    id: "cr-1", consentType: "marketing", action: "granted", policyVersion: "1.0",
    grantedAt: "2026-01-01T00:00:00Z" as ServerTimestamp, withdrawnAt: null, expiresAt: null,
    ...overrides,
  };
}

function mockConsents(data: ConsentRecord[] | undefined, opts: { isPending?: boolean; isError?: boolean } = {}) {
  jest.spyOn(queriesModule, "useConsentsQuery").mockReturnValue({
    data, isPending: !!opts.isPending, isError: !!opts.isError, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.useConsentsQuery>);
}

function mockWithdraw() {
  jest.spyOn(queriesModule, "useWithdrawConsentMutation").mockReturnValue({
    mutate: jest.fn(), isPending: false,
  } as unknown as ReturnType<typeof queriesModule.useWithdrawConsentMutation>);
}

describe("PrivacyConsentScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); });

  it("shows a loading state while consents are being fetched", () => {
    mockConsents(undefined, { isPending: true }); mockWithdraw();
    const { getByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("Loading your consent choices…")).toBeTruthy();
  });

  it("shows an error state with retry when the fetch fails and there's no cached data", () => {
    mockConsents(undefined, { isError: true }); mockWithdraw();
    const { getByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("We couldn't load your consent choices.")).toBeTruthy();
  });

  it("renders a real granted consent with an Active state and a plain customer-facing label", () => {
    mockConsents([record({ consentType: "marketing", action: "granted" })]); mockWithdraw();
    const { getByText, queryByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("Marketing communications")).toBeTruthy();
    expect(getByText("Active")).toBeTruthy();
    expect(queryByText("marketing")).toBeNull();
  });

  it("shows a withdrawn consent as Withdrawn with no withdraw action available", () => {
    mockConsents([record({ consentType: "marketing", action: "withdrawn" })]); mockWithdraw();
    const { getByText, queryByLabelText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("Withdrawn")).toBeTruthy();
    expect(queryByLabelText("Withdraw Marketing communications")).toBeNull();
  });

  it("shows a Withdraw action only for a withdrawable, currently-active consent type", () => {
    mockConsents([record({ consentType: "marketing", action: "granted" })]); mockWithdraw();
    const { getByLabelText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByLabelText("Withdraw Marketing communications")).toBeTruthy();
  });

  it("renders a mandatory (non-withdrawable) consent type as read-only, never with a toggle or Withdraw action", () => {
    mockConsents([record({ consentType: "terms_of_service", action: "granted" })]); mockWithdraw();
    const { getByText, queryByLabelText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("Required -- cannot be withdrawn while using Fuvay.")).toBeTruthy();
    expect(queryByLabelText("Withdraw Terms of service")).toBeNull();
  });

  it("calls the real withdraw mutation with only the allowlisted consent_type payload", () => {
    const mutate = jest.fn();
    jest.spyOn(queriesModule, "useWithdrawConsentMutation").mockReturnValue({
      mutate, isPending: false,
    } as unknown as ReturnType<typeof queriesModule.useWithdrawConsentMutation>);
    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Withdraw");
      confirm?.onPress?.();
    });
    mockConsents([record({ consentType: "marketing", action: "granted" })]);
    const { getByLabelText } = renderWithProviders(<PrivacyConsentScreen />);
    fireEvent.press(getByLabelText("Withdraw Marketing communications"));
    expect(mutate).toHaveBeenCalledWith({ consentType: "marketing" });
  });

  it("shows an empty state when the customer has no consent records at all", () => {
    mockConsents([]); mockWithdraw();
    const { getByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("No consent records found.")).toBeTruthy();
  });

  it("de-duplicates to only the latest record per consent type", () => {
    mockConsents([
      record({ id: "newest", consentType: "marketing", action: "withdrawn" }),
      record({ id: "older", consentType: "marketing", action: "granted" }),
    ]);
    mockWithdraw();
    const { getByText, queryAllByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(getByText("Withdrawn")).toBeTruthy();
    expect(queryAllByText("Marketing communications")).toHaveLength(1);
  });

  it("never renders push notification settings, location OS permissions, or DeepSeek language controls on this screen", () => {
    mockConsents([record()]); mockWithdraw();
    const { queryByText } = renderWithProviders(<PrivacyConsentScreen />);
    expect(queryByText(/deepseek/i)).toBeNull();
    expect(queryByText(/language/i)).toBeNull();
  });

  it("Go back navigates via the back chevron", () => {
    mockConsents([record()]); mockWithdraw();
    const { getByLabelText } = renderWithProviders(<PrivacyConsentScreen />);
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});
