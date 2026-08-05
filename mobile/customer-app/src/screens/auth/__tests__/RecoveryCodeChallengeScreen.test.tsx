import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { RecoveryCodeChallengeScreen } from "../RecoveryCodeChallengeScreen";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

describe("RecoveryCodeChallengeScreen", () => {
  afterEach(() => jest.restoreAllMocks());

  it("submits a non-numeric recovery code through the same completeMfaChallenge call as the TOTP screen", async () => {
    const spy = jest.spyOn(sessionManager, "completeMfaChallenge").mockResolvedValue({
      authenticated: true, audience: "serviceos:customer", customerId: "c-1" as never, tenantId: null, accountStatus: "active",
    });
    const { getByLabelText, getByText } = renderAuthScreen("RecoveryCodeChallenge", RecoveryCodeChallengeScreen);
    fireEvent.changeText(getByLabelText("Recovery code"), "ABCD-1234");
    fireEvent.press(getByText("Verify"));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("ABCD-1234"));
  });

  it("clears the code and shows a safe error on an already-used recovery code", async () => {
    jest.spyOn(sessionManager, "completeMfaChallenge").mockRejectedValue(
      new DomainError({ category: "AUTH_REQUIRED", diagnostic: "Invalid MFA code." }),
    );
    const { getByLabelText, getByText, findByText } = renderAuthScreen("RecoveryCodeChallenge", RecoveryCodeChallengeScreen);
    fireEvent.changeText(getByLabelText("Recovery code"), "ABCD-1234");
    fireEvent.press(getByText("Verify"));
    await findByText(/couldn't sign you in/i);
    expect(getByLabelText("Recovery code").props.value).toBe("");
  });

  it("does not show a remaining-recovery-code count (no customer-safe field exists for it)", () => {
    const { queryByText } = renderAuthScreen("RecoveryCodeChallenge", RecoveryCodeChallengeScreen);
    expect(queryByText(/remaining/i)).toBeNull();
  });
});
