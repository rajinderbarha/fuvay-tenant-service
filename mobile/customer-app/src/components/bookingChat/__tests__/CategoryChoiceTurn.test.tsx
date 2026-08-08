import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CategoryChoiceTurn } from "../CategoryChoiceTurn";
import { HomeCategory } from "../../../domain/customerHome";
import { asCategoryId } from "../../../domain/ids";

function category(name: string, slug: string): HomeCategory {
  return {
    categoryId: asCategoryId(`cat-${slug}`),
    name,
    slug,
    iconUrl: null,
    description: null,
    startingPrice: null,
  } as HomeCategory;
}

const CATEGORIES = [
  category("Air Conditioning", "air-conditioning"),
  category("Plumbing", "plumbing"),
];

describe("CategoryChoiceTurn", () => {
  it("asks which service instead of assuming one", () => {
    // The bug: the Assistant tab kept the params of the last service tapped on
    // Home, so a bare tab tap opened straight into that category's questions.
    renderWithProviders(
      <CategoryChoiceTurn categories={CATEGORIES} loading={false} city="Ludhiana" onSelect={() => {}} />,
    );
    expect(screen.getByText("Which service do you need?")).toBeTruthy();
    expect(screen.getByText("Air Conditioning")).toBeTruthy();
    expect(screen.getByText("Plumbing")).toBeTruthy();
  });

  it("reports the chosen category so the real conversation can start", () => {
    const onSelect = jest.fn();
    renderWithProviders(
      <CategoryChoiceTurn categories={CATEGORIES} loading={false} city={null} onSelect={onSelect} />,
    );
    fireEvent.press(screen.getByText("Plumbing"));
    expect(onSelect).toHaveBeenCalledWith(CATEGORIES[1]);
  });

  it("offers only what the backend says is bookable here", () => {
    // No hardcoded menu: an empty list is an honest answer about this ZIP, not
    // a reason to show a default category.
    renderWithProviders(
      <CategoryChoiceTurn categories={[]} loading={false} city="Ludhiana" onSelect={() => {}} />,
    );
    expect(screen.getByText("No services here yet")).toBeTruthy();
    expect(screen.getByText(/aren't serving Ludhiana yet/)).toBeTruthy();
    expect(screen.queryByText("Which service do you need?")).toBeNull();
  });

  it("says it is still checking rather than claiming nothing is available", () => {
    renderWithProviders(
      <CategoryChoiceTurn categories={[]} loading city={null} onSelect={() => {}} />,
    );
    expect(screen.getByText(/Checking what's available near you/)).toBeTruthy();
    expect(screen.queryByText("No services here yet")).toBeNull();
  });
});
