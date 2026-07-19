import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { ThemeProvider, useTheme } from "../theme/ThemeProvider";

function Probe() {
  const { resolvedTheme, toggle } = useTheme();
  return (
    <div>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button onClick={toggle}>toggle</button>
    </div>
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to light and sets data-theme on <html>", () => {
    render(
      <ThemeProvider defaultPreference="light">
        <Probe />
      </ThemeProvider>
    );
    expect(screen.getByTestId("resolved").textContent).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggles theme and persists the preference to localStorage", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider defaultPreference="light">
        <Probe />
      </ThemeProvider>
    );
    await act(async () => {
      await user.click(screen.getByText("toggle"));
    });
    expect(screen.getByTestId("resolved").textContent).toBe("dark");
    expect(window.localStorage.getItem("serviceos-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
