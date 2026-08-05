import React from "react";
import { Appearance } from "react-native";
import { render, act, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";
import { ThemeProvider, useTheme } from "../theme/ThemeProvider";

function ModeProbe() {
  const { mode, preference, setPreference, isLoaded } = useTheme();
  return (
    <>
      <Text testID="mode">{mode}</Text>
      <Text testID="preference">{preference}</Text>
      <Text testID="loaded">{String(isLoaded)}</Text>
      <Text testID="set-dark" onPress={() => setPreference("dark")}>set-dark</Text>
      <Text testID="set-light" onPress={() => setPreference("light")}>set-light</Text>
    </>
  );
}

describe("ThemeProvider", () => {
  it("defaults to the system color scheme when preference is 'system'", async () => {
    jest.spyOn(Appearance, "getColorScheme").mockReturnValue("dark");
    const { getByTestId } = render(
      <ThemeProvider>
        <ModeProbe />
      </ThemeProvider>,
    );
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    expect(getByTestId("mode").props.children).toBe("dark");
  });

  it("switches to an explicit light preference", async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <ModeProbe />
      </ThemeProvider>,
    );
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    await act(async () => {
      getByTestId("set-light").props.onPress();
    });
    expect(getByTestId("mode").props.children).toBe("light");
  });

  it("switches to an explicit dark preference", async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <ModeProbe />
      </ThemeProvider>,
    );
    await waitFor(() => expect(getByTestId("loaded").props.children).toBe("true"));
    await act(async () => {
      getByTestId("set-dark").props.onPress();
    });
    expect(getByTestId("mode").props.children).toBe("dark");
  });

  it("throws a clear error when useTheme is used outside the provider", () => {
    function Bare() {
      useTheme();
      return null;
    }
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Bare />)).toThrow("useTheme must be used within a ThemeProvider");
    spy.mockRestore();
  });
});
