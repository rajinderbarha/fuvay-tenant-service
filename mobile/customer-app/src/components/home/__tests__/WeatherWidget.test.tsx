import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { WeatherWidget } from "../WeatherWidget";
import { HomeWeather } from "../../../domain/customerHome";

function weather(overrides: Partial<HomeWeather> = {}): HomeWeather {
  return {
    observedAt: "2026-08-12T14:00:00Z",
    temperatureC: 29.4,
    condition: "Partly cloudy",
    rainMm: 0,
    windKmh: 8,
    ...overrides,
  };
}

describe("WeatherWidget", () => {
  it("renders nothing at all without a reading", () => {
    // The rule the whole weather feature is built on: no source, no widget. A
    // placeholder "--°" or a cheerful default would undermine every real figure
    // beside it.
    const { queryByText } = renderWithProviders(
      <WeatherWidget weather={null} city="Ludhiana" seasonLabel="Monsoon picks" />,
    );
    expect(queryByText(/°C/)).toBeNull();
    expect(queryByText("Ludhiana")).toBeNull();
  });

  it("shows the real temperature with the place it applies to", () => {
    renderWithProviders(
      <WeatherWidget weather={weather()} city="Ludhiana" seasonLabel="Monsoon picks" />,
    );
    expect(screen.getByText("29°C")).toBeTruthy();
    expect(screen.getByText("Partly cloudy")).toBeTruthy();
    // The seasonal wording sits here because it explains the ordering below.
    expect(screen.getByText("Ludhiana · Monsoon picks")).toBeTruthy();
  });

  it("calls out rain only when there is enough of it to matter", () => {
    const { queryByText } = renderWithProviders(
      <WeatherWidget weather={weather({ rainMm: 0.2 })} city={null} />,
    );
    expect(queryByText(/mm/)).toBeNull();

    renderWithProviders(<WeatherWidget weather={weather({ rainMm: 12.5 })} city={null} />);
    expect(screen.getByText("12.5 mm")).toBeTruthy();
  });

  it("says nothing about the sky when the provider sent no wording", () => {
    renderWithProviders(<WeatherWidget weather={weather({ condition: null })} city="Ludhiana" />);
    expect(screen.getByText("29°C")).toBeTruthy();
    // No invented description to fill the gap.
    expect(screen.queryByText(/cloudy|sunny|clear/i)).toBeNull();
  });

  it("reads the temperature out for screen readers with its place", () => {
    renderWithProviders(<WeatherWidget weather={weather()} city="Ludhiana" />);
    expect(screen.getByLabelText("29 degrees in Ludhiana, Partly cloudy")).toBeTruthy();
  });

  it("still renders with no city, rather than inventing one", () => {
    renderWithProviders(<WeatherWidget weather={weather()} city={null} />);
    expect(screen.getByText("29°C")).toBeTruthy();
  });
});
