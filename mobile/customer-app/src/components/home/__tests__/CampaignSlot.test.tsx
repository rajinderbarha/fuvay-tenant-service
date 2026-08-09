import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CampaignSlot } from "../CampaignSlot";
import { HomeCampaign, HomeCampaignPlacement, HomeCampaignStyle } from "../../../domain/customerHome";

function campaign(overrides: Partial<HomeCampaign> = {}): HomeCampaign {
  return {
    campaignId: "c-1",
    eyebrow: null,
    title: "Monsoon Home Care",
    description: null,
    artworkUrlLight: null,
    artworkUrlDark: null,
    ctaLabel: "Book now",
    ctaDeeplink: "app://category/air-conditioning",
    priority: 10,
    style: "hero" as HomeCampaignStyle,
    placement: "campaign_top" as HomeCampaignPlacement,
    accentColor: null,
    badgeText: null,
    endsAt: null,
    ...overrides,
  };
}

const routable = () => true;
const unroutable = () => false;

describe("CampaignSlot", () => {
  it("renders nothing for a slot with no campaigns", () => {
    const { toJSON } = renderWithProviders(
      <CampaignSlot placement="campaign_mid" campaigns={[campaign()]} mode="light"
                    isCtaRoutable={routable} onPressCta={() => {}} />,
    );
    // The top-placed campaign must not leak into the mid slot.
    expect(JSON.stringify(toJSON())).not.toContain("Monsoon");
  });

  it("draws a festival banner with its badge and real end date", () => {
    renderWithProviders(
      <CampaignSlot
        placement="campaign_mid"
        campaigns={[campaign({
          campaignId: "c-f", style: "festival", placement: "campaign_mid",
          title: "Get your home festival-ready", badgeText: "Diwali Special",
          accentColor: "#f59e0b", endsAt: "2026-11-05T18:29:59Z",
        })]}
        mode="light" isCtaRoutable={routable} onPressCta={() => {}}
      />,
    );
    expect(screen.getByText("Get your home festival-ready")).toBeTruthy();
    expect(screen.getByText("Diwali Special")).toBeTruthy();
    expect(screen.getByText("Ends 5 Nov")).toBeTruthy();
  });

  it("states no deadline for an open-ended campaign rather than inventing urgency", () => {
    renderWithProviders(
      <CampaignSlot
        placement="campaign_mid"
        // Title deliberately free of the words being asserted against -- the
        // default "Monsoon Home Care" contains "soon".
        campaigns={[campaign({
          style: "festival", placement: "campaign_mid", endsAt: null,
          title: "Festive home care",
        })]}
        mode="light" isCtaRoutable={routable} onPressCta={() => {}}
      />,
    );
    expect(screen.queryByText(/Ends/)).toBeNull();
    expect(screen.queryByText(/soon|hurry|last/i)).toBeNull();
  });

  it("draws a strip as one tappable line", () => {
    const onPressCta = jest.fn();
    const strip = campaign({
      campaignId: "c-s", style: "strip", placement: "campaign_bottom",
      title: "Need it today? Same-day slots are open", ctaLabel: "See slots",
    });
    renderWithProviders(
      <CampaignSlot placement="campaign_bottom" campaigns={[strip]} mode="light"
                    isCtaRoutable={routable} onPressCta={onPressCta} />,
    );
    fireEvent.press(screen.getByLabelText("Need it today? Same-day slots are open. See slots"));
    expect(onPressCta).toHaveBeenCalledWith(strip);
  });

  it("leaves a strip as plain text when its link goes nowhere", () => {
    // A row that looks pressable and does nothing reads as a broken app.
    const onPressCta = jest.fn();
    renderWithProviders(
      <CampaignSlot
        placement="campaign_bottom"
        campaigns={[campaign({ style: "strip", placement: "campaign_bottom", ctaLabel: "See slots" })]}
        mode="light" isCtaRoutable={unroutable} onPressCta={onPressCta}
      />,
    );
    expect(screen.queryByText("See slots")).toBeNull();
    expect(screen.getByText("Monsoon Home Care")).toBeTruthy();
  });

  it("drops the festival CTA rather than rendering a dead button", () => {
    renderWithProviders(
      <CampaignSlot
        placement="campaign_mid"
        campaigns={[campaign({ style: "festival", placement: "campaign_mid" })]}
        mode="light" isCtaRoutable={unroutable} onPressCta={() => {}}
      />,
    );
    expect(screen.queryByLabelText("Book now")).toBeNull();
    expect(screen.getByText("Not available at your location yet")).toBeTruthy();
  });

  it("pages a slot holding several banners, keeping each in its own style", () => {
    // Two festival banners stacked ate half the screen, so a slot with more than
    // one banner swipes -- and each page keeps its own treatment rather than
    // being flattened into a single carousel style.
    renderWithProviders(
      <CampaignSlot
        placement="campaign_mid"
        campaigns={[
          campaign({ campaignId: "a", style: "festival", placement: "campaign_mid", title: "Diwali offer", badgeText: "Diwali Special" }),
          campaign({ campaignId: "b", style: "strip", placement: "campaign_mid", title: "Same-day slots" }),
        ]}
        mode="light" isCtaRoutable={routable} onPressCta={() => {}}
      />,
    );
    expect(screen.getByLabelText("Promotional offers, 2 available")).toBeTruthy();
    expect(screen.getByText("Diwali offer")).toBeTruthy();
    expect(screen.getByText("Diwali Special")).toBeTruthy();
    expect(screen.getByText("Same-day slots")).toBeTruthy();
  });

  it("does not wrap a lone banner in a pager", () => {
    // A one-page carousel is a card with a swipe gesture that does nothing, and
    // a single dot implies content that is not there.
    renderWithProviders(
      <CampaignSlot
        placement="campaign_mid"
        campaigns={[campaign({ style: "festival", placement: "campaign_mid" })]}
        mode="light" isCtaRoutable={routable} onPressCta={() => {}}
      />,
    );
    expect(screen.queryByLabelText(/Promotional offers/)).toBeNull();
  });

  it("serves every slot the backend can target", () => {
    // A slot the app cannot draw would let admin schedule a banner into a void.
    const slots: HomeCampaignPlacement[] = [
      "campaign_top", "campaign_after_problems", "campaign_after_services",
      "campaign_mid", "campaign_bottom",
    ];
    for (const placement of slots) {
      const view = renderWithProviders(
        <CampaignSlot
          placement={placement}
          campaigns={[campaign({ campaignId: `c-${placement}`, placement, title: `In ${placement}` })]}
          mode="light" isCtaRoutable={routable} onPressCta={() => {}}
        />,
      );
      expect(view.getByText(`In ${placement}`)).toBeTruthy();
      view.unmount();
    }
  });
});
