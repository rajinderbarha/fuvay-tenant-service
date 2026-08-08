import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ProviderTrustCard } from "../ProviderTrustCard";
import { ReviewProvider, ReviewProviderFacts } from "../../../domain/bookingReview";

function facts(overrides: Partial<ReviewProviderFacts> = {}): ReviewProviderFacts {
  return {
    verified: true,
    rating: 4.8,
    reviewCount: 42,
    jobsCompleted: 118,
    completionRate: 96,
    onPlatformSince: "2025-03-01T00:00:00Z",
    city: "Ludhiana",
    isNew: false,
    ...overrides,
  };
}

function provider(overrides: Partial<ReviewProvider> = {}): ReviewProvider {
  return {
    tenantId: "t1",
    providerName: "Guramrit",
    publicBadges: [{ name: "Verified", icon: null, color: null }],
    rating: 4.8,
    facts: facts(),
    ...overrides,
  };
}

describe("ProviderTrustCard", () => {
  it("shows the real rating with its review count", () => {
    renderWithProviders(<ProviderTrustCard provider={provider()} />);
    expect(screen.getByText("Guramrit")).toBeTruthy();
    expect(screen.getByText("4.8")).toBeTruthy();
    expect(screen.getByText("(42 reviews)")).toBeTruthy();
  });

  it("shows real job and completion figures", () => {
    renderWithProviders(<ProviderTrustCard provider={provider()} />);
    expect(screen.getByText("118")).toBeTruthy();
    expect(screen.getByText("jobs done")).toBeTruthy();
    expect(screen.getByText("96%")).toBeTruthy();
  });

  it("says the provider is new instead of implying a track record", () => {
    // The live bug this replaces: the API added a "Verified" badge
    // unconditionally, so a provider with no history at all was presented as
    // verified with high completion.
    renderWithProviders(
      <ProviderTrustCard
        provider={provider({
          publicBadges: [],
          rating: null,
          facts: facts({
            verified: false, rating: null, reviewCount: 0,
            jobsCompleted: 0, completionRate: null, isNew: true,
          }),
        })}
      />,
    );
    expect(screen.getByText(/New on Fuvay — no reviews yet/)).toBeTruthy();
    // No fabricated figures anywhere.
    expect(screen.queryByText("jobs done")).toBeNull();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.queryByText("0")).toBeNull();
  });

  it("does not present a thin rating as a headline stat", () => {
    // One five-star review is real but is not a track record. It is stated with
    // its count rather than as a big "5.0".
    renderWithProviders(
      <ProviderTrustCard
        provider={provider({ rating: 5, facts: facts({ rating: 5, reviewCount: 1 }) })}
      />,
    );
    expect(screen.getByText(/5\.0 from 1 review/)).toBeTruthy();
    expect(screen.queryByText("(1 reviews)")).toBeNull();
  });

  it("withholds a completion rate the backend judged insufficient", () => {
    renderWithProviders(
      <ProviderTrustCard
        provider={provider({ facts: facts({ completionRate: null, jobsCompleted: 2 }) })}
      />,
    );
    expect(screen.getByText("2")).toBeTruthy();       // the real count is fine
    expect(screen.queryByText(/%/)).toBeNull();        // the rate is not invented
  });

  it("renders only the badges the backend authored", () => {
    renderWithProviders(
      <ProviderTrustCard
        provider={provider({ publicBadges: [{ name: "Highly Rated", icon: null, color: null }] })}
      />,
    );
    expect(screen.getByText("Highly Rated")).toBeTruthy();
    // "Verified" was not in the list, so it must not appear as a chip.
    expect(screen.queryByText("Verified")).toBeNull();
  });

  it("states a rating with no known count without claiming there are no reviews", () => {
    // An older payload predating `facts` still carries a rating. Saying
    // "no reviews yet" beside a 4.8 would contradict itself.
    renderWithProviders(<ProviderTrustCard provider={provider({ facts: null })} />);
    expect(screen.getByText("Guramrit")).toBeTruthy();
    expect(screen.getByText(/4\.8 average rating/)).toBeTruthy();
    expect(screen.queryByText(/no reviews yet/)).toBeNull();
  });

  it("says New only when there is genuinely no rating at all", () => {
    renderWithProviders(
      <ProviderTrustCard provider={provider({ rating: null, facts: null })} />,
    );
    expect(screen.getByText(/New on Fuvay — no reviews yet/)).toBeTruthy();
  });
});
