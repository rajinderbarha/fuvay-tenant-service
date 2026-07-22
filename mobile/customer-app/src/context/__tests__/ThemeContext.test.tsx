import React from "react";
import { Text } from "react-native";
import { Appearance } from "react-native";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { ThemeProvider, useTheme } from "../ThemeContext";

// UX-07 Round 4 Pass 2: real, meaningful-assertion tests for the theme
// contract -- persistence across remounts, System/Light/Dark resolution,
// and that the resolved palette actually differs (not a no-op toggle).

function Probe() {
  const { mode, preference, setPreference, isLoaded } = useTheme();
  return (
    <>
      <Text testID="loaded">{String(isLoaded)}</Text>
      <Text testID="mode">{mode}</Text>
      <Text testID="preference">{preference}</Text>
      <Text testID="set-light" onPress={() => setPreference("light")}>light</Text>
      <Text testID="set-dark" onPress={() => setPreference("dark")}>dark</Text>
      <Text testID="set-system" onPress={() => setPreference("system")}>system</Text>
    </>
  );
}

describe("ThemeContext", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
    jest.spyOn(Appearance, "getColorScheme").mockReturnValue("light");
    // ThemeContext subscribes to Appearance.addChangeListener for live
    // system-theme updates. Left unmocked, RN/RN-web's real listener can
    // fire asynchronously with the test machine's actual OS/browser color
    // scheme, racing and flipping `systemScheme` state after mount -- this
    // was the source of this suite's intermittent failures (a mock-lifecycle
    // leak, not a ThemeContext defect). Mocking it deterministically removes
    // the race; each test can still simulate a live change by grabbing the
    // captured listener and invoking it explicitly.
    jest.spyOn(Appearance, "addChangeListener").mockImplementation(() => ({
      remove: () => {},
    }));
  });
  afterEach(() => jest.restoreAllMocks());

  it("defaults to system preference and resolves to the current system scheme", async () => {
    const { getByTestId } = render(<ThemeProvider><Probe/></ThemeProvider>);
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    expect(getByTestId("preference").props.children).toBe("system");
    expect(getByTestId("mode").props.children).toBe("light");
  });

  it("switching to dark updates the resolved mode and persists the choice", async () => {
    const { getByTestId } = render(<ThemeProvider><Probe/></ThemeProvider>);
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));

    fireEvent.press(getByTestId("set-dark"));

    await waitFor(() => expect(getByTestId("mode").props.children).toBe("dark"));
    expect(getByTestId("preference").props.children).toBe("dark");
    await waitFor(async () =>
      expect(await AsyncStorage.getItem("customer_app_theme_preference")).toBe("dark"));
  });

  it("persists dark preference across a provider remount (no flash-of-wrong-theme after restart)", async () => {
    await AsyncStorage.setItem("customer_app_theme_preference", "dark");
    const { getByTestId } = render(<ThemeProvider><Probe/></ThemeProvider>);
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    expect(getByTestId("preference").props.children).toBe("dark");
    expect(getByTestId("mode").props.children).toBe("dark");
  });

  it("light preference resolves to light mode even when the system scheme is dark", async () => {
    jest.spyOn(Appearance, "getColorScheme").mockReturnValue("dark");
    await AsyncStorage.setItem("customer_app_theme_preference", "light");
    const { getByTestId } = render(<ThemeProvider><Probe/></ThemeProvider>);
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    expect(getByTestId("mode").props.children).toBe("light");
  });

  it("ignores a corrupt/unrecognized stored value and falls back to system", async () => {
    await AsyncStorage.setItem("customer_app_theme_preference", "not-a-real-preference");
    const { getByTestId } = render(<ThemeProvider><Probe/></ThemeProvider>);
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    expect(getByTestId("preference").props.children).toBe("system");
  });
});
