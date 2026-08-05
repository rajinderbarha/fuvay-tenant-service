import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { MfaChallengeScreen } from "../MfaChallengeScreen";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

describe("MfaChallengeScreen", () => {
  afterEach(() => jest.restoreAllMocks());

  it("submits the 6-digit authenticator code via completeMfaChallenge", async () => {
    const spy = jest.spyOn(sessionManager, "completeMfaChallenge").mockResolvedValue({
      authenticated: true, audience: "serviceos:customer", customerId: "c-1" as never, tenantId: null, accountStatus: "active",
    });
    const { getByLabelText } = renderAuthScreen("MfaChallenge", MfaChallengeScreen);
    fireEvent.changeText(getByLabelText("Verification code"), "445566");
    await waitFor(() => expect(spy).toHaveBeenCalledWith("445566"));
  });

  it("shows an inline error and clears the code on an invalid attempt, never authenticating", async () => {
    jest.spyOn(sessionManager, "completeMfaChallenge").mockRejectedValue(
      new DomainError({ category: "AUTH_REQUIRED", diagnostic: "Invalid MFA code." }),
    );
    const { getByLabelText, findByText } = renderAuthScreen("MfaChallenge", MfaChallengeScreen);
    fireEvent.changeText(getByLabelText("Verification code"), "000000");
    await findByText(/couldn't sign you in/i);
    expect(getByLabelText("Verification code").props.value).toBe("");
  });

  it("offers a route to the recovery-code screen", () => {
    const { getByText } = renderAuthScreen("MfaChallenge", MfaChallengeScreen);
    expect(getByText("Use a recovery code")).toBeTruthy();
  });
});
