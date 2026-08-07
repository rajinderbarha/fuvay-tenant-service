import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AttachmentsSummary } from "../AttachmentsSummary";

describe("AttachmentsSummary detail sheet", () => {
  it("opens real photo/note content on 'View details' rather than linking to a nonexistent screen", () => {
    // No dedicated attachments screen exists anywhere in this app; the
    // link must open something real, built from data this card already
    // has, not point at a route that 404s.
    const { getByText, queryByText } = renderWithProviders(
      <AttachmentsSummary
        attachments={[{ id: "a-1", url: "/uploads/photo.jpg" }]}
        note="Please call before arriving"
      />,
    );
    // The summary row already shows the note text as its own chip label,
    // so what proves the sheet actually opened is the dedicated
    // "Additional note" section heading, which only exists inside it.
    expect(queryByText("Additional note")).toBeNull();
    fireEvent.press(getByText("View details"));
    expect(getByText("Additional note")).toBeTruthy();
  });

  it("hides the link entirely when there is nothing to show details of", () => {
    const { queryByText } = renderWithProviders(<AttachmentsSummary attachments={[]} note={null} />);
    expect(queryByText("View details")).toBeNull();
  });
});
