import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { LoginMethodScreen } from "../LoginMethodScreen";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

describe("LoginMethodScreen", () => {
  afterEach(() => jest.restoreAllMocks());

  it("does not show 'New customers can continue with OTP' (no JIT creation on the backend)", () => {
    const { queryByText } = renderAuthScreen("LoginMethod", LoginMethodScreen);
    expect(queryByText(/New customers can continue with OTP/i)).toBeNull();
  });

  it("shows a validation error for an incomplete mobile number instead of submitting", async () => {
    const spy = jest.spyOn(sessionManager, "requestLoginOtp");
    const { getByLabelText, getByText, findByText } = renderAuthScreen("LoginMethod", LoginMethodScreen);
    fireEvent.changeText(getByLabelText("Mobile number"), "987");
    fireEvent.press(getByText("Send code"));
    await findByText(/valid 10-digit mobile number/i);
    expect(spy).not.toHaveBeenCalled();
  });

  it("requests an OTP for a valid number and does not reveal account existence on failure", async () => {
    jest.spyOn(sessionManager, "requestLoginOtp").mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "some internal detail" }),
    );
    const { getByLabelText, getByText, findByText } = renderAuthScreen("LoginMethod", LoginMethodScreen);
    fireEvent.changeText(getByLabelText("Mobile number"), "9876543210");
    fireEvent.press(getByText("Send code"));
    const banner = await findByText(/check the details you entered/i);
    expect(banner).toBeTruthy();
  });

  it("prevents a second submission while the first request is in flight", async () => {
    let resolveFn: () => void = () => {};
    const spy = jest.spyOn(sessionManager, "requestLoginOtp").mockReturnValue(
      new Promise(resolve => { resolveFn = () => resolve(undefined as never); }),
    );
    const { getByLabelText, getByRole } = renderAuthScreen("LoginMethod", LoginMethodScreen);
    fireEvent.changeText(getByLabelText("Mobile number"), "9876543210");
    const continueButton = getByRole("button", { name: "Send code" });
    fireEvent.press(continueButton);
    fireEvent.press(continueButton);
    resolveFn();
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
  });
});
