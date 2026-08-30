import React from "react";

import { renderWithProviders } from "../../testing/renderWithProviders";
import { SplashScreen } from "../SplashScreen";

/**
 * No fake timers here on purpose. This suite originally used them to drive
 * the animation sequence, which deadlocked the project's global async
 * `afterEach` cleanup (jest.after-env.js) and timed out every test in the
 * file. The animation drivers are fire-and-forget and stopped on unmount, so
 * what is worth asserting -- that the screen renders, announces itself, and
 * tears down cleanly -- needs no timer control.
 */
describe("SplashScreen", () => {
  it("renders the v2 splash copy", () => {
    const { getByText } = renderWithProviders(<SplashScreen />);
    expect(getByText("HOME SERVICES, DONE RIGHT")).toBeTruthy();
    expect(getByText("LOADING YOUR HOME")).toBeTruthy();
  });

  it("exposes itself to assistive tech as loading progress", () => {
    // A splash that announces nothing leaves a screen-reader user on a
    // silent screen with no indication the app is working.
    const { getByLabelText } = renderWithProviders(<SplashScreen />);
    expect(getByLabelText("Loading Fuvay")).toBeTruthy();
  });

  it("labels the wordmark rather than leaving a bare image", () => {
    // Queried by label, not role: RN's Image does not surface an "image"
    // role to the testing library even with accessibilityRole set.
    const { getByLabelText } = renderWithProviders(<SplashScreen />);
    expect(getByLabelText("Fuvay")).toBeTruthy();
  });

  it("unmounts cleanly mid-animation", () => {
    // This screen is unmounted the moment bootstrap resolves, usually well
    // before the 2.6s track fill completes -- that must not throw or leave
    // a driver attached to a torn-down tree.
    const { unmount } = renderWithProviders(<SplashScreen />);
    expect(() => unmount()).not.toThrow();
  });
});
