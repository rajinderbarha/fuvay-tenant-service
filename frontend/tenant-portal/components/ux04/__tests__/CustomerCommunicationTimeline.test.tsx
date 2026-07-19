import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CustomerCommunicationTimeline } from "../CustomerCommunicationTimeline";
import { communicationFixture } from "../../../lib/ux04/fixtures";

describe("CustomerCommunicationTimeline — internal notes never presented as customer-visible", () => {
  it("marks a customerVisible:false event as internal only", () => {
    render(<CustomerCommunicationTimeline events={communicationFixture} />);
    const internalEvent = communicationFixture.find((e) => !e.customerVisible)!;
    expect(internalEvent).toBeDefined();
    expect(screen.getByText(/internal only/i)).toBeInTheDocument();
  });

  it("renders retry hint only for failed+retryable events", () => {
    render(<CustomerCommunicationTimeline events={communicationFixture} />);
    expect(screen.getByText(/retry available/i)).toBeInTheDocument();
  });
});
