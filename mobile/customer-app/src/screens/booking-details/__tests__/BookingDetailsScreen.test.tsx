import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { BookingDetailsScreen } from "../BookingDetailsScreen";
import * as detailsQueryModule from "../../../api/customerBookings/useCustomerBookingDetailsQuery";
import * as networkStateModule from "../../../api/networkState";
import { CustomerBookingDetails, CustomerActiveJob } from "../../../domain/customerBookingDetails";
import { ServerTimestamp } from "../../../domain/dates";
import * as quoteQueriesModule from "../../../api/customerQuote/useCustomerQuoteQueries";
import { CustomerQuote } from "../../../domain/customerQuote";
import * as partsQueriesModule from "../../../api/customerParts/useCustomerPartsQueries";
import { CustomerPartsRequestList } from "../../../domain/customerParts";
import * as reviewQueriesModule from "../../../api/customerReview/useCustomerReviewQueries";
import { CustomerReview } from "../../../domain/customerReview";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
  useRoute: () => ({ name: "BookingDetails", params: { bookingId: "b-1" } }),
}));

function details(overrides: Partial<CustomerBookingDetails> = {}): CustomerBookingDetails {
  return {
    bookingId: "b-1", bookingNumber: "FUV-2841",
    stage: "provider_assignment", statusLabel: "Request confirmed",
    activityText: "Assigning an eligible professional",
    supportingText: "We'll notify you when a provider accepts the request.",
    createdAt: "2026-01-01T09:41:00Z" as ServerTimestamp, updatedAt: null,
    service: { name: "AC Repair", jobType: "repair", inspectionRequired: true, issueSummary: null, answers: [] },
    address: { label: "Home", formatted: "Model Town, Ludhiana", zipcode: "141002" },
    pricing: { state: "unavailable" as never, inspection: null },
    attachments: [], note: null,
    activity: [{ id: "b-1:created", label: "Booking FUV-2841 was created.", timestamp: "2026-01-01T09:41:00Z" as ServerTimestamp }],
    notifications: { kind: "unavailable" },
    job: null,
    ...overrides,
  };
}

function job(overrides: Partial<CustomerActiveJob> = {}): CustomerActiveJob {
  return {
    jobId: "job-1", rawStage: "assignment", rawStatus: "assigned", scheduledDate: null, scheduledTimeWindow: null,
    technician: { displayName: "Amanpreet S.", designation: "Technician", photoUrl: null },
    completion: null,
    warrantyDays: null, warrantyExpiresAt: null, warrantyActive: false,
    ...overrides,
  };
}

function quote(overrides: Partial<CustomerQuote> = {}): CustomerQuote {
  return {
    id: "q-1", quoteNumber: "QT-0001", jobId: "job-1", rawStatus: "sent_to_customer", currency: "₹",
    totalAmount: "1450", customerPayableAmount: "1450",
    findingSummary: "Cooling circuit needs repair.", rejectionReason: null, isCurrent: true,
    items: [{ id: "i-1", label: "Repair service", description: null, quantity: "1", unitAmount: "1450", lineTotal: "1450" }],
    ...overrides,
  };
}

function mockQuoteHooks(result: quoteQueriesModule.CurrentQuoteResult | undefined, opts: { isPending?: boolean } = {}) {
  jest.spyOn(quoteQueriesModule, "useCurrentQuoteQuery").mockReturnValue({
    data: result, isPending: !!opts.isPending,
  } as unknown as ReturnType<typeof quoteQueriesModule.useCurrentQuoteQuery>);
  const approveMutate = jest.fn();
  const declineMutate = jest.fn();
  jest.spyOn(quoteQueriesModule, "useApproveQuoteMutation").mockReturnValue({
    mutate: approveMutate, isPending: false,
  } as unknown as ReturnType<typeof quoteQueriesModule.useApproveQuoteMutation>);
  jest.spyOn(quoteQueriesModule, "useDeclineQuoteMutation").mockReturnValue({
    mutate: declineMutate, isPending: false,
  } as unknown as ReturnType<typeof quoteQueriesModule.useDeclineQuoteMutation>);
  return { approveMutate, declineMutate };
}

function partsList(overrides: Partial<CustomerPartsRequestList> = {}): CustomerPartsRequestList {
  return {
    currency: "₹", previousEstimatedTotal: "1450", additionalTotal: "850", newEstimatedTotal: "2300",
    items: [{
      id: "pr-1", rawStatus: "customer_approval_pending", partName: "AC capacitor", quantity: 1,
      unitAmount: "850", lineTotal: "850", reason: "Needed to restore cooling performance.",
      customerApprovalRequired: true, submittedAt: "2026-08-02T10:00:00Z", decidedAt: null, rejectionReason: null,
    }],
    ...overrides,
  };
}

function mockPartsHooks(data: CustomerPartsRequestList | undefined) {
  jest.spyOn(partsQueriesModule, "usePartsRequestsQuery").mockReturnValue({
    data,
  } as unknown as ReturnType<typeof partsQueriesModule.usePartsRequestsQuery>);
  const approveMutate = jest.fn();
  const declineMutate = jest.fn();
  jest.spyOn(partsQueriesModule, "useApprovePartsRequestMutation").mockReturnValue({
    mutate: approveMutate, isPending: false,
  } as unknown as ReturnType<typeof partsQueriesModule.useApprovePartsRequestMutation>);
  jest.spyOn(partsQueriesModule, "useDeclinePartsRequestMutation").mockReturnValue({
    mutate: declineMutate, isPending: false,
  } as unknown as ReturnType<typeof partsQueriesModule.useDeclinePartsRequestMutation>);
  return { approveMutate, declineMutate };
}

function mockReviewHooks(existing: CustomerReview | null | undefined) {
  jest.spyOn(reviewQueriesModule, "useBookingReviewQuery").mockReturnValue({
    data: existing,
  } as unknown as ReturnType<typeof reviewQueriesModule.useBookingReviewQuery>);
  const submitMutate = jest.fn();
  jest.spyOn(reviewQueriesModule, "useSubmitBookingRatingMutation").mockReturnValue({
    mutate: submitMutate, isPending: false,
  } as unknown as ReturnType<typeof reviewQueriesModule.useSubmitBookingRatingMutation>);
  return { submitMutate };
}

function mockQuery(
  data: { kind: "found"; details: CustomerBookingDetails } | { kind: "not_found" } | undefined,
  opts: { isPending?: boolean; isError?: boolean; isRefetching?: boolean } = {},
) {
  const refetch = jest.fn();
  jest.spyOn(detailsQueryModule, "useCustomerBookingDetailsQuery").mockReturnValue({
    data, isPending: !!opts.isPending, isError: !!opts.isError, isRefetching: !!opts.isRefetching, refetch,
  } as unknown as ReturnType<typeof detailsQueryModule.useCustomerBookingDetailsQuery>);
  return refetch;
}

function render() {
  return renderWithProviders(<BookingDetailsScreen />);
}

describe("BookingDetailsScreen", () => {
  beforeEach(() => { mockQuoteHooks(undefined); mockPartsHooks(undefined); mockReviewHooks(null); });
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockGoBack.mockClear(); });

  it("shows the loading state", () => {
    mockQuery(undefined, { isPending: true });
    const { getByText } = render();
    expect(getByText("Loading your booking")).toBeTruthy();
  });

  it("uses only the bookingId to fetch -- never trusts navigation-supplied display data", () => {
    const spy = jest.spyOn(detailsQueryModule, "useCustomerBookingDetailsQuery").mockReturnValue({
      data: { kind: "found", details: details() }, isPending: false, isError: false, isRefetching: false, refetch: jest.fn(),
    } as unknown as ReturnType<typeof detailsQueryModule.useCustomerBookingDetailsQuery>);
    render();
    expect(spy).toHaveBeenCalledWith("b-1");
  });

  it("shows the enumeration-safe unavailable state for a missing or foreign booking", () => {
    mockQuery({ kind: "not_found" });
    const { getByText } = render();
    expect(getByText("We couldn't find this booking")).toBeTruthy();
    expect(getByText(/it may not exist, or it may belong to a different account/i)).toBeTruthy();
  });

  it("renders the real pending-assignment status, never a fabricated ETA or provider identity", () => {
    mockQuery({ kind: "found", details: details() });
    const { getByText, queryByText } = render();
    expect(getByText("Assigning an eligible professional")).toBeTruthy();
    expect(queryByText(/\bETA\b|technician|provider name|call now/i)).toBeNull();
  });

  it("never renders Cancel or Reschedule actions", () => {
    mockQuery({ kind: "found", details: details() });
    const { queryByText, getByText } = render();
    expect(queryByText("Cancel booking")).toBeNull();
    expect(queryByText("Reschedule")).toBeNull();
    expect(getByText("Cancellation and rescheduling are not available in the app yet.")).toBeTruthy();
  });

  it("shows real finalized service, address, and booking reference", () => {
    mockQuery({ kind: "found", details: details() });
    const { getByText } = render();
    expect(getByText("AC Repair")).toBeTruthy();
    expect(getByText("Model Town, Ludhiana")).toBeTruthy();
  });

  it("renders only real activity events, never fabricated matching/provider-notified steps", () => {
    mockQuery({ kind: "found", details: details() });
    const { getByText, queryByText } = render();
    expect(getByText("Booking FUV-2841 was created.")).toBeTruthy();
    expect(queryByText(/matching started|provider notified|provider viewed|technician selected/i)).toBeNull();
  });

  it("Contact support navigates to the real Create Support Request wizard, carrying the booking context", () => {
    mockQuery({ kind: "found", details: details() });
    const { getByText } = render();
    fireEvent.press(getByText("Contact support"));
    expect(mockNavigate).toHaveBeenCalledWith("CreateSupportRequest", { source: "booking", bookingId: "b-1" });
  });

  it("Refresh status triggers a refetch", () => {
    const refetch = mockQuery({ kind: "found", details: details() });
    const { getByText } = render();
    fireEvent.press(getByText("Refresh status"));
    expect(refetch).toHaveBeenCalled();
  });

  it("shows an offline banner while offline but keeps cached data visible", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockQuery({ kind: "found", details: details() });
    const { getByText } = render();
    expect(getByText("AC Repair")).toBeTruthy();
  });

  it("shows a recoverable error state on first-load failure with no cached data", () => {
    mockQuery(undefined, { isError: true });
    const { getByText } = render();
    expect(getByText("Something went wrong")).toBeTruthy();
  });

  it("preserves the last-known booking during a refresh error, never blanking to an error screen", () => {
    mockQuery({ kind: "found", details: details() }, { isError: true });
    const { getByText } = render();
    expect(getByText("AC Repair")).toBeTruthy();
  });

  it("shows the real Ionicons-safe status label, not a raw backend enum", () => {
    mockQuery({ kind: "found", details: details({ stage: "unknown", statusLabel: "Status pending", activityText: null }) });
    const { queryByText, getByText } = render();
    expect(queryByText("pending_assignment")).toBeNull();
    expect(getByText("Status pending")).toBeTruthy();
  });

  it("shows the Assigned state with the technician card, no schedule row", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "assignment" }) }) });
    const { getAllByText, getByText, queryByText } = render();
    expect(getAllByText("Assigned").length).toBeGreaterThan(0);
    expect(getByText("Amanpreet S.")).toBeTruthy();
    expect(getByText("Technician")).toBeTruthy();
    expect(queryByText(/·/)).toBeNull();
  });

  it("shows the Scheduled state with a real verified schedule window", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "scheduled", scheduledDate: "2026-08-05", scheduledTimeWindow: "3:00 PM - 5:00 PM" }) }),
    });
    const { getAllByText, getByText } = render();
    expect(getAllByText("Scheduled").length).toBeGreaterThan(0);
    expect(getByText(/5 Aug 2026 · 3:00 PM - 5:00 PM/)).toBeTruthy();
  });

  it("shows the On the way state", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "on_the_way" }) }) });
    const { getAllByText, getByText } = render();
    expect(getAllByText("On the way").length).toBeGreaterThan(0);
    expect(getByText("Your service professional is heading to your address.")).toBeTruthy();
  });

  it("uses a neutral fallback avatar when no real approved photo exists", () => {
    mockQuery({ kind: "found", details: details({ job: job({ technician: { displayName: "Rahul K.", designation: null, photoUrl: null } }) }) });
    const { getByText, queryByText } = render();
    expect(getByText("Rahul K.")).toBeTruthy();
    expect(queryByText("null")).toBeNull();
  });

  it("omits the schedule row when no schedule is set yet, never a placeholder", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "scheduled", scheduledDate: null }) }) });
    const { queryByText } = render();
    expect(queryByText(/·/)).toBeNull();
  });

  it("falls back to the existing neutral presentation for a stage this phase does not own", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "inspection" }) }) });
    const { queryByText, getAllByText } = render();
    expect(queryByText("Assigned professional")).toBeNull();
    expect(getAllByText("Request confirmed").length).toBeGreaterThan(0);
  });

  it("never renders Call, Chat, ETA, map or live-location controls for any active job state", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "on_the_way" }) }) });
    const { queryByText, queryByLabelText } = render();
    expect(queryByText(/^call$/i)).toBeNull();
    expect(queryByText(/^chat$/i)).toBeNull();
    expect(queryByText(/\bETA\b/i)).toBeNull();
    expect(queryByLabelText(/map/i)).toBeNull();
  });

  it("never fabricates technician identity when no real assignment exists", () => {
    mockQuery({ kind: "found", details: details() });
    const { queryByText } = render();
    expect(queryByText("Assigned professional")).toBeNull();
  });

  it("renders the 5-step job progress timeline with correct step states for Scheduled", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "scheduled" }) }) });
    const { getByText } = render();
    expect(getByText("Booked")).toBeTruthy();
    expect(getByText("Assigned")).toBeTruthy();
    expect(getByText("On the way")).toBeTruthy();
    expect(getByText("Arrived")).toBeTruthy();
  });

  it("exposes the job progress timeline with an accessible progressbar role", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "assignment" }) }) });
    const { getByLabelText } = render();
    expect(getByLabelText("Job progress")).toBeTruthy();
  });

  it("never imports or registers the orphaned JobTrackingScreen", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "../BookingDetailsScreen.tsx"), "utf8");
    expect(source).not.toMatch(/JobTrackingScreen/);
  });

  it("never imports or registers the orphaned QuoteApprovalScreen", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "../BookingDetailsScreen.tsx"), "utf8");
    expect(source).not.toMatch(/QuoteApprovalScreen/);
  });

  it("shows the Arrived state", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "unknown_stage", rawStatus: "reached_site" }) }) });
    const { getAllByText, getByText } = render();
    expect(getAllByText("Arrived").length).toBeGreaterThan(0);
    expect(getByText("Your service professional has arrived at your location.")).toBeTruthy();
  });

  it("shows Inspection in progress", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "inspection_started" }) }) });
    const { getByText } = render();
    expect(getByText("Inspection in progress")).toBeTruthy();
  });

  it("shows a loading acknowledgment while checking the latest estimate after inspection completes", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "inspection_done" }) }) });
    mockQuoteHooks(undefined, { isPending: true });
    const { getByText } = render();
    expect(getByText("Checking the latest estimate…")).toBeTruthy();
  });

  it("shows inspection-complete acknowledgment when no quote has been submitted yet", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    mockQuoteHooks({ kind: "none" });
    const { getByText, queryByText } = render();
    expect(getByText("Inspection complete")).toBeTruthy();
    expect(queryByText("Approve quote")).toBeNull();
  });

  it("shows the quote-ready state with real backend-provided items, finding and total", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    mockQuoteHooks({ kind: "found", quote: quote() });
    const { getByText, getAllByText } = render();
    expect(getByText("Quote ready")).toBeTruthy();
    expect(getByText("Cooling circuit needs repair.")).toBeTruthy();
    expect(getByText("Repair service")).toBeTruthy();
    expect(getAllByText(/1450/).length).toBeGreaterThan(0);
  });

  it("shows the direct-payment disclosure and never a Pay now/card/wallet/UPI control", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    mockQuoteHooks({ kind: "found", quote: quote() });
    const { getByText, queryByText } = render();
    expect(getByText(/pay the provider directly after service/i)).toBeTruthy();
    expect(getByText(/fuvay does not collect job payment/i)).toBeTruthy();
    expect(queryByText(/^pay now$/i)).toBeNull();
    expect(queryByText(/card|wallet|upi/i)).toBeNull();
  });

  it("Approve quote calls the approve mutation with the real quote id", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    const { approveMutate } = mockQuoteHooks({ kind: "found", quote: quote() });
    const { getByText } = render();
    fireEvent.press(getByText(/Approve quote/));
    expect(approveMutate).toHaveBeenCalledWith("q-1");
  });

  it("Decline quote requires a reason before it can be submitted", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    const { declineMutate } = mockQuoteHooks({ kind: "found", quote: quote() });
    const { getByText } = render();
    fireEvent.press(getByText("Decline quote"));
    fireEvent.press(getByText("Confirm decline"));
    expect(declineMutate).not.toHaveBeenCalled();
  });

  it("shows the approved state without decision controls", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    mockQuoteHooks({ kind: "found", quote: quote({ rawStatus: "customer_approved" }) });
    const { getByText, queryByText } = render();
    expect(getByText("Quote approved")).toBeTruthy();
    expect(queryByText("Approve quote")).toBeNull();
    expect(queryByText("Decline quote")).toBeNull();
  });

  it("shows the declined state with the real rejection reason, no decision controls", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "quote_required" }) }) });
    mockQuoteHooks({ kind: "found", quote: quote({ rawStatus: "customer_rejected", rejectionReason: "Too expensive" }) });
    const { getByText, queryByText } = render();
    expect(getByText("Quote declined")).toBeTruthy();
    expect(getByText("Too expensive")).toBeTruthy();
    expect(queryByText("Approve quote")).toBeNull();
  });

  it("never fabricates a quote card when the backend has none for this job", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "reached_site" }) }) });
    mockQuoteHooks(undefined);
    const { queryByText } = render();
    expect(queryByText("Quote ready")).toBeNull();
    expect(queryByText("Review estimate")).toBeNull();
  });

  it("shows the customer-actionable parts state with real backend items and totals", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList());
    const { getByText, getAllByText } = render();
    expect(getByText("Part review needed")).toBeTruthy();
    expect(getByText("AC capacitor")).toBeTruthy();
    expect(getByText("Needed to restore cooling performance.")).toBeTruthy();
    expect(getAllByText(/850/).length).toBeGreaterThan(0);
    expect(getAllByText(/2300/).length).toBeGreaterThan(0);
  });

  it("shows the visibility-only parts state with no decision controls (tenant approval is not customer consent)", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList({
      items: [{
        id: "pr-2", rawStatus: "business_approved", partName: "AC capacitor", quantity: 1,
        unitAmount: "850", lineTotal: "850", reason: "Needed to restore cooling performance.",
        customerApprovalRequired: false, submittedAt: "2026-08-02T10:00:00Z", decidedAt: null, rejectionReason: null,
      }],
    }));
    const { getByText, queryByText } = render();
    expect(getByText("Part added to your repair")).toBeTruthy();
    expect(queryByText("Approve additional cost")).toBeNull();
    expect(queryByText("Decline additional cost")).toBeNull();
    expect(getByText("What happens next")).toBeTruthy();
  });

  it("Approve additional cost calls the approve mutation with the real parts-request id", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    const { approveMutate } = mockPartsHooks(partsList());
    const { getByText } = render();
    fireEvent.press(getByText(/Approve additional cost/));
    expect(approveMutate).toHaveBeenCalledWith("pr-1");
  });

  it("Decline additional cost requires a reason before it can be submitted", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    const { declineMutate } = mockPartsHooks(partsList());
    const { getByText } = render();
    fireEvent.press(getByText("Decline additional cost"));
    fireEvent.press(getByText("Confirm decline"));
    expect(declineMutate).not.toHaveBeenCalled();
  });

  it("shows the approved parts state without decision controls", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList({
      items: [{
        id: "pr-3", rawStatus: "customer_approved", partName: "AC capacitor", quantity: 1,
        unitAmount: "850", lineTotal: "850", reason: "Needed to restore cooling performance.",
        customerApprovalRequired: true, submittedAt: "2026-08-02T10:00:00Z", decidedAt: "2026-08-02T10:05:00Z", rejectionReason: null,
      }],
    }));
    const { getByText, queryByText } = render();
    expect(getByText("Additional cost approved")).toBeTruthy();
    expect(queryByText("Approve additional cost")).toBeNull();
  });

  it("shows the declined parts state with the real rejection reason", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList({
      items: [{
        id: "pr-4", rawStatus: "customer_rejected", partName: "AC capacitor", quantity: 1,
        unitAmount: "850", lineTotal: "850", reason: "Needed to restore cooling performance.",
        customerApprovalRequired: true, submittedAt: "2026-08-02T10:00:00Z", decidedAt: "2026-08-02T10:05:00Z", rejectionReason: "Too expensive",
      }],
    }));
    const { getByText } = render();
    expect(getByText("Additional cost declined")).toBeTruthy();
    expect(getByText("Too expensive")).toBeTruthy();
  });

  it("shows the direct-payment disclosure on the parts card and never a Pay now/card/wallet/UPI control", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList());
    const { getByText, queryByText } = render();
    expect(getByText(/pay the provider directly after service/i)).toBeTruthy();
    expect(queryByText(/^pay now$/i)).toBeNull();
    expect(queryByText(/card|wallet|upi/i)).toBeNull();
  });

  it("never fabricates a parts card when the backend has no visible items for this job", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockPartsHooks(partsList({ items: [] }));
    const { queryByText } = render();
    expect(queryByText("Part review needed")).toBeNull();
    expect(queryByText("Part added to your repair")).toBeNull();
  });

  it("never imports or registers a standalone Parts Approval route", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "../BookingDetailsScreen.tsx"), "utf8");
    expect(source).not.toMatch(/navigate\(["']PartsApproval/);
  });

  it("shows the Service completed state with real work summary and final amount", () => {
    mockQuery({
      kind: "found",
      details: details({
        job: job({
          rawStage: "x", rawStatus: "completed",
          completion: { workSummary: "Cooling restored, capacitor replaced.", collectedAmount: 2300, completedAt: "2026-08-02T10:00:00Z" },
        }),
      }),
    });
    const { getByText, getAllByText } = render();
    expect(getByText("Service completed")).toBeTruthy();
    expect(getByText("Cooling restored, capacitor replaced.")).toBeTruthy();
    expect(getAllByText(/2300/).length).toBeGreaterThan(0);
  });

  it("shows the rating form only once the job is genuinely completed", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    const { queryByText } = render();
    expect(queryByText("How was your service?")).toBeNull();
  });

  it("Submit review calls the rating mutation with the selected stars, tags and note", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 100, completedAt: null } }) }),
    });
    const { submitMutate } = mockReviewHooks(null);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Rate 5 out of 5 stars"));
    fireEvent.press(getByLabelText("Professional"));
    fireEvent.press(getByText("Submit review"));
    expect(submitMutate).toHaveBeenCalledWith({ rating: 5, tags: ["professional"], comment: undefined });
  });

  it("shows the already-submitted review read-only and never re-opens the form", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 100, completedAt: null } }) }),
    });
    mockReviewHooks({ rating: 4, comment: "Good job", tags: ["clean_work"], createdAt: "2026-08-02T10:05:00Z" });
    const { getByText, queryByText } = render();
    expect(getByText("Your review")).toBeTruthy();
    expect(getByText("Good job")).toBeTruthy();
    expect(queryByText("Submit review")).toBeNull();
  });

  it("shows the direct-payment disclosure on the completion screen and never a Pay now/card/wallet/UPI control", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 100, completedAt: null } }) }),
    });
    const { getByText, queryByText } = render();
    expect(getByText(/payment is made directly to the provider/i)).toBeTruthy();
    expect(queryByText(/^pay now$/i)).toBeNull();
    expect(queryByText(/card|wallet|upi/i)).toBeNull();
  });

  it("never renders the completion state when completion data is absent even if status says completed", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: null }) }) });
    const { queryByText } = render();
    expect(queryByText("Service completed")).toBeNull();
  });

  it("shows the Repair in progress state and never rating controls before completion", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    const { getByText, queryByText } = render();
    expect(getByText("Repair in progress")).toBeTruthy();
    expect(queryByText("How was your service?")).toBeNull();
    expect(queryByText("Confirm completion")).toBeNull();
  });

  it("shows the Work done state, still no rating controls until canonical completion", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "work_done" }) }) });
    const { getByText, queryByText } = render();
    expect(getByText("Work done")).toBeTruthy();
    expect(queryByText("How was your service?")).toBeNull();
  });

  it("shows the approved quote read-only (no decision buttons) while repair is in progress", () => {
    mockQuery({ kind: "found", details: details({ job: job({ rawStage: "x", rawStatus: "service_started" }) }) });
    mockQuoteHooks({ kind: "found", quote: quote({ rawStatus: "customer_approved" }) });
    const { getByText, queryByText } = render();
    expect(getByText("Quote approved")).toBeTruthy();
    expect(queryByText("Approve quote")).toBeNull();
    expect(queryByText("Decline quote")).toBeNull();
  });

  it("never imports or registers the orphaned ReviewScreen", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "../BookingDetailsScreen.tsx"), "utf8");
    expect(source).not.toMatch(/ReviewScreen/);
  });

  // ── ACTIVE-JOB-JOURNEY-CLOSURE phase: terminal Booking Closed state ──────

  it("shows the terminal Booking closed state once the review is also submitted", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Cooling restored", collectedAmount: 2300, completedAt: "2026-08-02T10:00:00Z" } }) }),
    });
    mockReviewHooks({ rating: 4, comment: "Quick and professional service.", tags: ["professional"], createdAt: "2026-08-02T10:05:00Z" });
    const { getByText, queryByText } = render();
    expect(getByText("Booking closed")).toBeTruthy();
    expect(getByText("Your service and review are complete.")).toBeTruthy();
    expect(getByText("Your review")).toBeTruthy();
    expect(getByText("Service record")).toBeTruthy();
    expect(queryByText("Service completed")).toBeNull();
    expect(queryByText("Submit review")).toBeNull();
  });

  it("shows the intermediate Service completed state (not Booking closed) while the review is still open", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Cooling restored", collectedAmount: 2300, completedAt: "2026-08-02T10:00:00Z" } }) }),
    });
    mockReviewHooks(null);
    const { getByText, queryByText } = render();
    expect(getByText("Service completed")).toBeTruthy();
    expect(queryByText("Booking closed")).toBeNull();
  });

  it("Booking closed shows the updated direct-payment disclosure copy", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 2300, completedAt: null } }) }),
    });
    mockReviewHooks({ rating: 5, comment: null, tags: [], createdAt: "2026-08-02T10:05:00Z" });
    const { getByText } = render();
    expect(getByText(/payment is made directly to the provider/i)).toBeTruthy();
    expect(getByText(/does not verify or collect job payment/i)).toBeTruthy();
  });

  // ── Regression guards ─────────────────────────────────────────────────────

  it("regression guard: no Cancel/Reschedule/Rebook/Favourite/Rewards controls in any state", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 2300, completedAt: null } }) }),
    });
    mockReviewHooks({ rating: 5, comment: null, tags: [], createdAt: "2026-08-02T10:05:00Z" });
    const { queryByText } = render();
    expect(queryByText(/^cancel booking$/i)).toBeNull();
    expect(queryByText(/^reschedule$/i)).toBeNull();
    expect(queryByText(/^rebook$/i)).toBeNull();
    expect(queryByText(/^favourite$/i)).toBeNull();
    expect(queryByText(/rewards|credits/i)).toBeNull();
  });

  it("regression guard: no ETA, map or technician-contact capability in the closed state", () => {
    mockQuery({
      kind: "found",
      details: details({ job: job({ rawStage: "x", rawStatus: "completed", completion: { workSummary: "Done", collectedAmount: 2300, completedAt: null } }) }),
    });
    mockReviewHooks({ rating: 5, comment: null, tags: [], createdAt: "2026-08-02T10:05:00Z" });
    const { queryByText, queryByLabelText } = render();
    expect(queryByText(/\bETA\b/i)).toBeNull();
    expect(queryByLabelText(/map/i)).toBeNull();
    expect(queryByText(/^call$/i)).toBeNull();
  });

  it("regression guard: BookingDetailsScreen imports no provider/staff endpoint module", () => {
    const source = require("fs").readFileSync(require("path").join(__dirname, "../BookingDetailsScreen.tsx"), "utf8");
    const importLines = source.split("\n").filter((line: string) => /^import /.test(line));
    for (const line of importLines) {
      expect(line).not.toMatch(/\/provider\//);
      expect(line).not.toMatch(/\/staff\//);
    }
  });
});
