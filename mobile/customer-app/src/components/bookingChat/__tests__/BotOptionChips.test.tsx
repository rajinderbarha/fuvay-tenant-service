import React from "react";
import { render, screen } from "@testing-library/react-native";
import { AppProviders } from "../../../providers/AppProviders";
import { BotOptionChips } from "../BotPrimitives";

describe("BotOptionChips", () => {
  it("renders one action when the catalog repeats the same label", () => {
    render(
      <AppProviders>
        <BotOptionChips
          items={["Unusual noise or vibration", "Unusual noise or vibration"]}
          selected={null}
          onSelect={jest.fn()}
        />
      </AppProviders>,
    );

    expect(screen.getAllByLabelText("Unusual noise or vibration")).toHaveLength(1);
  });
});
