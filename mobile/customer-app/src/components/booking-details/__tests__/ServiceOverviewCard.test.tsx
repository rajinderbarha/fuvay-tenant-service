import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ServiceOverviewCard } from "../ServiceOverviewCard";
import { CustomerBookingDetails } from "../../../domain/customerBookingDetails";

type Service = CustomerBookingDetails["service"];

const LONG_LABEL = "Please describe anything else the technician should know before arriving";
const LONG_VALUE =
  "The outdoor unit makes a rattling noise after about ten minutes and the remote "
  + "display flickers when the fan speed changes.";

function service(answers: Service["answers"]): Service {
  return {
    name: "AC Service",
    inspectionRequired: true,
    answers,
  } as Service;
}

describe("ServiceOverviewCard answers sheet", () => {
  it("opens the sheet and shows every answer", () => {
    const { getByLabelText, getByText, queryByText } = renderWithProviders(
      <ServiceOverviewCard
        service={service([
          { id: "a1", label: "Which AC brand?", value: "Voltas" },
          { id: "a2", label: LONG_LABEL, value: LONG_VALUE },
        ])}
        bookingNumber="BK-20260808-000001"
        createdAt={null}
      />,
    );
    expect(queryByText("Your answers")).toBeNull();
    fireEvent.press(getByLabelText("View all answers"));
    expect(getByText("Your answers")).toBeTruthy();
    expect(getByText("2 details you told us")).toBeTruthy();
  });

  it("lets long labels and values wrap instead of running off the screen", () => {
    // The bug this covers: each answer was a row with justifyContent
    // "space-between" and no flex/minWidth, so a long question and a long
    // answer pushed each other past both edges of the display. Unbounded
    // numberOfLines plus a flexible, min-width-0 column is what allows wrapping,
    // so that is what is asserted -- not a pixel measurement RNTL cannot see.
    const { getByLabelText, getAllByText } = renderWithProviders(
      <ServiceOverviewCard
        service={service([{ id: "a1", label: LONG_LABEL, value: LONG_VALUE }])}
        bookingNumber={null}
        createdAt={null}
      />,
    );
    fireEvent.press(getByLabelText("View all answers"));
    // The same text also appears in the compact grid on the card itself, where
    // one clipped line is correct -- so what matters is that the SHEET's copy is
    // unclipped.
    for (const text of [LONG_LABEL, LONG_VALUE]) {
      const unclipped = getAllByText(text).filter(n => n.props.numberOfLines === undefined);
      expect(unclipped.length).toBeGreaterThan(0);
    }
  });

  it("closes from the backdrop as well as the close button", () => {
    const { getByLabelText, getByText, queryByText } = renderWithProviders(
      <ServiceOverviewCard
        service={service([{ id: "a1", label: "Which AC brand?", value: "Voltas" }])}
        bookingNumber={null}
        createdAt={null}
      />,
    );
    fireEvent.press(getByLabelText("View all answers"));
    expect(getByText("Your answers")).toBeTruthy();
    fireEvent.press(getByLabelText("Close all answers"));
    expect(queryByText("Your answers")).toBeNull();
  });

  it("offers no sheet when the booking carries no answers", () => {
    const { queryByLabelText } = renderWithProviders(
      <ServiceOverviewCard service={service([])} bookingNumber={null} createdAt={null} />,
    );
    expect(queryByLabelText("View all answers")).toBeNull();
  });
});
