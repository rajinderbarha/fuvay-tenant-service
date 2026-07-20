import React from "react";
import { Text } from "react-native";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../themes/theme-provider";
import { useAppTheme } from "../themes/use-app-theme";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { PREFERENCE_STORAGE_KEYS } from "../../storage/storage-keys";

jest.mock("react-native/Libraries/Utilities/useColorScheme", () => ({
  __esModule: true,
  default: jest.fn(() => "dark"),
}));

function Probe() {
  const { mode, preference, setPreference } = useAppTheme();
  return (
    <>
      <Text testID="mode">{mode}</Text>
      <Text testID="preference">{preference}</Text>
      <Text testID="set-dark" onPress={() => setPreference("dark")}>
        set-dark
      </Text>
      <Text testID="set-light" onPress={() => setPreference("light")}>
        set-light
      </Text>
    </>
  );
}

describe("ThemeProvider", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it("resolves system mode using the device color scheme when preference is system", async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => expect(getByTestId("preference").props.children).toBe("system"));
    expect(getByTestId("mode").props.children).toBe("dark");
  });

  it("explicit light preference overrides system", async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    fireEvent.press(getByTestId("set-light"));
    await waitFor(() => expect(getByTestId("mode").props.children).toBe("light"));
  });

  it("explicit dark preference overrides system", async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    fireEvent.press(getByTestId("set-dark"));
    await waitFor(() => expect(getByTestId("mode").props.children).toBe("dark"));
  });

  it("persists the preference across mounts", async () => {
    const first = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    fireEvent.press(first.getByTestId("set-light"));
    await waitFor(() => expect(first.getByTestId("mode").props.children).toBe("light"));
    first.unmount();

    const second = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => expect(second.getByTestId("preference").props.children).toBe("light"));
  });

  it("falls back to system when a corrupted preference value is persisted", async () => {
    await AsyncStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, JSON.stringify("not-a-real-preference"));
    const { getByTestId } = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => expect(getByTestId("preference").props.children).toBe("system"));
  });
});
