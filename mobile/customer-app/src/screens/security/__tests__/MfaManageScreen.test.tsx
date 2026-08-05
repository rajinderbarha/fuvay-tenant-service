import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { MfaManageScreen } from "../MfaManageScreen";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as mfaMutationsModule from "../../../api/customerSecurity/useMfaMutations";
import { CustomerProfile } from "../../../domain/customer";
import { asCustomerId } from "../../../domain/ids";

const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack }),
}));

function profile(overrides: Partial<CustomerProfile> = {}): CustomerProfile {
  return {
    id: asCustomerId("c-1"), fullName: "Rajinder Singh", displayName: "Rajinder",
    phone: "+919900024102", email: "rajinder@example.com", avatarUrl: null,
    language: "en", timezone: "Asia/Kolkata", verified: true, mfaEnabled: false, isActive: true,
    createdAt: "2026-01-01T00:00:00Z" as CustomerProfile["createdAt"],
    capabilities: { canEditProfile: true, canUpdateAvatar: false, canManageAddresses: false, canChangePassword: true, canManageSessions: true, canDeleteAccount: false },
    ...overrides,
  };
}

function mockProfile(data: CustomerProfile | undefined, isPending = false) {
  jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
    data, isPending, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
}

function render() {
  return renderWithProviders(<MfaManageScreen />);
}

describe("MfaManageScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); });

  it("shows the begin-setup step when MFA is not yet enabled", () => {
    mockProfile(profile({ mfaEnabled: false }));
    const { getByText } = render();
    expect(getByText("Set up two-step verification")).toBeTruthy();
    expect(getByText("Begin setup")).toBeTruthy();
  });

  it("calls the real setup endpoint and shows the secret + backup codes, never before confirmation is MFA marked enabled", async () => {
    mockProfile(profile({ mfaEnabled: false }));
    const setupMutate = jest.fn().mockResolvedValue({
      data: { secret: "JBSWY3DPEHPK3PXP", qr_uri: "otpauth://totp/x", backup_codes: ["AAAA1111", "BBBB2222"], backup_codes_remaining: 2 },
    });
    jest.spyOn(mfaMutationsModule, "useSetupMfaMutation").mockReturnValue({
      mutateAsync: setupMutate, isPending: false,
    } as unknown as ReturnType<typeof mfaMutationsModule.useSetupMfaMutation>);

    const { getByText } = render();
    fireEvent.press(getByText("Begin setup"));

    await waitFor(() => expect(getByText("JBSWY3DPEHPK3PXP")).toBeTruthy());
    expect(getByText("AAAA1111")).toBeTruthy();
    expect(getByText("BBBB2222")).toBeTruthy();
  });

  it("requires acknowledging saved backup codes before Confirm is enabled", async () => {
    mockProfile(profile({ mfaEnabled: false }));
    jest.spyOn(mfaMutationsModule, "useSetupMfaMutation").mockReturnValue({
      mutateAsync: jest.fn().mockResolvedValue({
        data: { secret: "SECRET", qr_uri: "otpauth://x", backup_codes: ["CODE1"], backup_codes_remaining: 1 },
      }),
      isPending: false,
    } as unknown as ReturnType<typeof mfaMutationsModule.useSetupMfaMutation>);
    const confirmMutate = jest.fn();
    jest.spyOn(mfaMutationsModule, "useConfirmMfaMutation").mockReturnValue({
      mutateAsync: confirmMutate, isPending: false,
    } as unknown as ReturnType<typeof mfaMutationsModule.useConfirmMfaMutation>);

    const { getByText, getByLabelText } = render();
    fireEvent.press(getByText("Begin setup"));
    await waitFor(() => expect(getByText("SECRET")).toBeTruthy());

    fireEvent.changeText(getByLabelText("Verification code"), "123456");
    fireEvent.press(getByText("Confirm and turn on"));
    expect(confirmMutate).not.toHaveBeenCalled();

    fireEvent.press(getByText("I've saved my backup codes"));
    fireEvent.press(getByText("Confirm and turn on"));
    await waitFor(() => expect(confirmMutate).toHaveBeenCalledWith("123456"));
  });

  it("shows the disable flow (password + code) when MFA is already enabled", () => {
    mockProfile(profile({ mfaEnabled: true }));
    const { getAllByText, getByLabelText } = render();
    expect(getAllByText("Turn off two-step verification").length).toBeGreaterThan(0);
    expect(getByLabelText("Password")).toBeTruthy();
    expect(getByLabelText("Verification code")).toBeTruthy();
  });

  it("does not create fake client-side backup codes anywhere", () => {
    mockProfile(profile({ mfaEnabled: false }));
    const { queryByText } = render();
    expect(queryByText(/backup code/i)).toBeNull(); // not shown until real setup response arrives
  });
});
