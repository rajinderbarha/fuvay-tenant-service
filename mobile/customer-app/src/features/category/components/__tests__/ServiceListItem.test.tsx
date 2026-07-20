import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithTheme } from "../../../../testing/render-with-theme";
import { ServiceListItem } from "../ServiceListItem";
import type { ValidatedOfferingSummary } from "../../domain/offering-schema";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string, opts?: Record<string, unknown>) => (opts?.price ? `Starting from ${opts.price}` : key) }),
}));

const offering: ValidatedOfferingSummary = {
  id: "off-1",
  name: "AC Repair",
  slug: "ac-repair",
  description: "Fix a broken AC unit",
  offering_class: "service",
  customer_flow_type: "diagnostic",
  primary_engine_key: null,
  pricing_model: "visit_based",
  starting_price: 199,
  visit_fee: 199,
  appointment_fee: 0,
  requires_type: false,
  requires_brand: false,
  requires_address: true,
  requires_slot: true,
  requires_photo_upload: false,
  is_available: true,
  display_order: 1,
};

describe("ServiceListItem", () => {
  it("renders the offering name and fires onPress with the offering", () => {
    const onPress = jest.fn();
    const { getByText } = renderWithTheme(<ServiceListItem offering={offering} locale="en" onPress={onPress} />);
    fireEvent.press(getByText("AC Repair"));
    expect(onPress).toHaveBeenCalledWith(offering);
  });

  it("does not render a price line when starting_price is zero", () => {
    const { queryByText } = renderWithTheme(<ServiceListItem offering={{ ...offering, starting_price: 0 }} locale="en" onPress={() => {}} />);
    expect(queryByText(/Starting from/)).toBeNull();
  });
});
