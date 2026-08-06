import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CampaignCarousel } from "../CampaignCarousel";

const campaign = {
  campaignId: "c-1", eyebrow: "Sponsored", title: "Monsoon Home Care", description: "Save more",
  artworkUrlLight: null, artworkUrlDark: null, ctaLabel: "Explore", ctaDeeplink: "app://offers", priority: 1,
};

describe("CampaignCarousel", () => {
  it("renders nothing when there are no campaigns", () => {
    const { queryByLabelText } = renderWithProviders(
      <CampaignCarousel campaigns={[]} mode="light" onPressCta={() => {}} isCtaRoutable={() => false} />,
    );
    expect(queryByLabelText(/Promotional offers/)).toBeNull();
  });

  it("replaces the CTA with an explanation when its deep link has no reachable destination", () => {
    // `app://offers` passes the backend allowlist but there is no offers
    // screen. This used to render a permanently greyed-out button, which
    // reads as a broken app rather than "not offered where you are" -- the
    // button is now dropped entirely in favour of a plain explanation, so
    // there is nothing left to press and nothing to navigate nowhere.
    const onPressCta = jest.fn();
    const { queryByText, getByText } = renderWithProviders(
      <CampaignCarousel campaigns={[campaign]} mode="light" onPressCta={onPressCta} isCtaRoutable={() => false} />,
    );
    expect(queryByText("Explore")).toBeNull();
    expect(getByText("Not available at your location yet")).toBeTruthy();
    expect(onPressCta).not.toHaveBeenCalled();
  });

  it("fires the CTA when its deep link resolves to a real destination", () => {
    const onPressCta = jest.fn();
    const routable = { ...campaign, ctaDeeplink: "app://category/home-services" };
    const { getByText } = renderWithProviders(
      <CampaignCarousel campaigns={[routable]} mode="light" onPressCta={onPressCta} isCtaRoutable={() => true} />,
    );
    fireEvent.press(getByText("Explore"));
    expect(onPressCta).toHaveBeenCalledWith(routable);
  });
});
