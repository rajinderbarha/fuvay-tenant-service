import React from "react";
import { View } from "react-native";
import { useRoute, RouteProp, useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { BookingDetailsHeader } from "../../components/booking-details/BookingDetailsHeader";
import { BookingDetailsSearchLauncher } from "../../components/booking-details/BookingDetailsSearchLauncher";
import { RequestJourneyStepper } from "../../components/booking-details/RequestJourneyStepper";
import { ServiceOverviewCard } from "../../components/booking-details/ServiceOverviewCard";
import { AttachmentsSummary } from "../../components/booking-details/AttachmentsSummary";
import { BookingActivity } from "../../components/booking-details/BookingActivity";
import { BookingDetailsActions } from "../../components/booking-details/BookingDetailsActions";
import { ActiveJobStatusCard } from "../../components/booking-details/ActiveJobStatusCard";
import { JobProgressTimeline } from "../../components/booking-details/JobProgressTimeline";
import { TechnicianSnapshotCard } from "../../components/booking-details/TechnicianSnapshotCard";
import { CurrentStatusCard } from "../../components/booking-confirmation/CurrentStatusCard";
import { FinalizedAddressCard } from "../../components/booking-confirmation/FinalizedAddressCard";
import { FinalizedPricingCard } from "../../components/booking-confirmation/FinalizedPricingCard";
import { BookingUpdatesCard } from "../../components/booking-confirmation/BookingUpdatesCard";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useCustomerBookingDetailsQuery } from "../../api/customerBookings/useCustomerBookingDetailsQuery";
import { isOffline } from "../../api/networkState";
import { resolveActiveJobStage, resolveActiveJobPresentation, formatScheduleWindow } from "../../domain/activeJobPresentation";
import { resolveArrivalInspectionStage, resolveArrivalInspectionPresentation, resolveQuoteDecisionStage } from "../../domain/inspectionQuotePresentation";
import { InspectionStatusCard } from "../../components/booking-details/InspectionStatusCard";
import { QuoteReviewCard } from "../../components/booking-details/QuoteReviewCard";
import { useCurrentQuoteQuery, useApproveQuoteMutation, useDeclineQuoteMutation } from "../../api/customerQuote/useCustomerQuoteQueries";
import { PartsApprovalCard } from "../../components/booking-details/PartsApprovalCard";
import { resolvePartsPresentationKind } from "../../domain/partsApprovalPresentation";
import { usePartsRequestsQuery, useApprovePartsRequestMutation, useDeclinePartsRequestMutation } from "../../api/customerParts/useCustomerPartsQueries";
import { WorkCompletedCard } from "../../components/booking-details/WorkCompletedCard";
import { RatingCard } from "../../components/booking-details/RatingCard";
import { useBookingReviewQuery, useSubmitBookingRatingMutation } from "../../api/customerReview/useCustomerReviewQueries";

type Route = RouteProp<CustomerAppStackParamList, "BookingDetails">;

/**
 * Authoritative Booking Details for the proven pending-assignment state
 * (spec mission). All display data comes from `bookingId` alone via
 * `useCustomerBookingDetailsQuery` -- no navigation param carries status/
 * pricing/provider/address (spec section 2).
 */
export function BookingDetailsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { bookingId } = route.params;
  const query = useCustomerBookingDetailsQuery(bookingId);

  const foundDetails = query.data?.kind === "found" ? query.data.details : null;
  const jobId = foundDetails?.job?.jobId ?? "";
  const arrivalStage = resolveArrivalInspectionStage(foundDetails?.job?.rawStatus);
  const quoteQueryEnabled = arrivalStage === "inspection_done" || arrivalStage === "in_progress" || arrivalStage === "work_done";
  const quoteQuery = useCurrentQuoteQuery(jobId, quoteQueryEnabled);
  const approveMutation = useApproveQuoteMutation(jobId);
  const declineMutation = useDeclineQuoteMutation(jobId);
  const partsQuery = usePartsRequestsQuery(jobId, !!jobId);
  const approvePartMutation = useApprovePartsRequestMutation(jobId);
  const declinePartMutation = useDeclinePartsRequestMutation(jobId);
  const isCompleted = foundDetails?.job?.rawStatus === "completed" && !!foundDetails?.job?.completion;
  const reviewQuery = useBookingReviewQuery(bookingId, isCompleted);
  const submitRatingMutation = useSubmitBookingRatingMutation(bookingId);

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your booking" />
      </AppScreen>
    );
  }

  if (isOffline() && !query.data) {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Reconnect to see your booking." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="Something went wrong" message="We couldn't load your booking." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.data?.kind !== "found") {
    return (
      <AppScreen>
        <ErrorState
          title="We couldn't find this booking"
          message="It may not exist, or it may belong to a different account."
          actionLabel="Go back"
          onAction={() => navigation.goBack()}
        />
      </AppScreen>
    );
  }

  const details = query.data.details;
  const activeStage = resolveActiveJobStage(details.job?.rawStage);
  const presentation = activeStage ? resolveActiveJobPresentation(activeStage) : null;
  const technician = details.job?.technician ?? null;

  const currentQuote = quoteQuery.data?.kind === "found" ? quoteQuery.data.quote : null;
  const decisionStage = currentQuote ? resolveQuoteDecisionStage(currentQuote.rawStatus) : null;
  const showQuoteReview = quoteQueryEnabled && currentQuote !== null;

  const parts = partsQuery.data ?? null;
  const partsItemKinds = (parts?.items ?? []).map(i => ({ item: i, kind: resolvePartsPresentationKind(i.rawStatus) }));
  // A pending customer decision always takes priority to surface; otherwise
  // show the most recent real state the backend proved (informational >
  // approved/declined). "unavailable" items are never shown at all.
  const partsFocus =
    partsItemKinds.find(x => x.kind === "actionable") ??
    partsItemKinds.find(x => x.kind === "informational") ??
    partsItemKinds.find(x => x.kind === "approved" || x.kind === "declined") ??
    null;
  const showPartsApproval = !!parts && parts.items.length > 0 && !!partsFocus;

  if (isCompleted && foundDetails?.job?.completion) {
    const completion = foundDetails.job.completion;
    // Mission's terminal "Booking closed" state: job complete AND review
    // complete, no pending customer decision remains. Reorders to Review
    // submitted -> Service record -> Final amount, matching the closed
    // permanent-record layout; the intermediate (review still open) state
    // keeps the original Service completed -> Work summary -> Rate order.
    const closed = !!reviewQuery.data;
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          {isOffline() ? <OfflineBanner /> : null}
          <BookingDetailsHeader
            bookingNumber={details.bookingNumber}
            onBack={() => navigation.goBack()}
            onRefresh={() => query.refetch()}
            refreshing={query.isRefetching}
          />
          {closed ? (
            <>
              <RatingCard
                existingReview={reviewQuery.data ?? null}
                submitting={submitRatingMutation.isPending}
                onSubmit={(rating, tags, comment) => submitRatingMutation.mutate({ rating, tags, comment: comment || undefined })}
              />
              <WorkCompletedCard serviceName={details.service.name} completion={completion} closed />
            </>
          ) : (
            <>
              <WorkCompletedCard serviceName={details.service.name} completion={completion} />
              <RatingCard
                existingReview={reviewQuery.data ?? null}
                submitting={submitRatingMutation.isPending}
                onSubmit={(rating, tags, comment) => submitRatingMutation.mutate({ rating, tags, comment: comment || undefined })}
              />
            </>
          )}
          <ServiceOverviewCard service={details.service} bookingNumber={details.bookingNumber} createdAt={details.createdAt} />
          <FinalizedAddressCard address={details.address} />
          <BookingActivity events={details.activity} />
          <BookingDetailsActions
            onRefresh={() => query.refetch()} refreshing={query.isRefetching}
            onContactSupport={() => (navigation as unknown as { navigate: (name: string, params?: object) => void })
              .navigate("CreateSupportRequest", { source: "booking", bookingId })}
          />
        </View>
      </AppScreen>
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        {isOffline() ? <OfflineBanner /> : null}
        <BookingDetailsHeader
          bookingNumber={details.bookingNumber}
          onBack={() => navigation.goBack()}
          onRefresh={() => query.refetch()}
          refreshing={query.isRefetching}
        />

        {showPartsApproval && parts && partsFocus ? (
          <PartsApprovalCard
            parts={parts}
            kind={partsFocus.kind}
            actionableItemId={partsFocus.kind === "actionable" ? partsFocus.item.id : null}
            approving={approvePartMutation.isPending}
            declining={declinePartMutation.isPending}
            onApprove={id => approvePartMutation.mutate(id)}
            onDecline={(id, reason) => declinePartMutation.mutate({ partsRequestId: id, reason })}
          />
        ) : showQuoteReview && currentQuote && decisionStage ? (
          <QuoteReviewCard
            quote={currentQuote}
            decisionStage={decisionStage}
            approving={approveMutation.isPending}
            declining={declineMutation.isPending}
            onApprove={() => approveMutation.mutate(currentQuote.id)}
            onDecline={reason => declineMutation.mutate({ quoteId: currentQuote.id, reason })}
          />
        ) : arrivalStage ? (
          quoteQuery.isPending && quoteQueryEnabled ? (
            <InspectionStatusCard presentation={{ title: resolveArrivalInspectionPresentation(arrivalStage).title, explanation: "Checking the latest estimate…" }} />
          ) : (
            <InspectionStatusCard presentation={resolveArrivalInspectionPresentation(arrivalStage)} />
          )
        ) : presentation ? (
          <ActiveJobStatusCard
            presentation={presentation}
            scheduleText={presentation.showSchedule ? formatScheduleWindow(details.job?.scheduledDate ?? null, details.job?.scheduledTimeWindow ?? null) : null}
          />
        ) : (
          <CurrentStatusCard
            statusLabel={details.statusLabel}
            activityText={details.activityText}
            supportingText={details.supportingText}
            createdAt={details.createdAt}
          />
        )}

        {/* This screen is already one specific booking, so the search/
            filter row cannot search "within" it -- BookingDetailsSearchLauncher
            hands both actions to My Bookings, the real list they act on,
            rather than being a control that does nothing here. */}
        <BookingDetailsSearchLauncher />

        {activeStage ? (
          <JobProgressTimeline activeStage={activeStage} />
        ) : arrivalStage ? (
          <JobProgressTimeline activeStage="arrived" />
        ) : (
          <RequestJourneyStepper stage={details.stage} />
        )}
        {(presentation?.showTechnicianCard || arrivalStage) && technician ? <TechnicianSnapshotCard technician={technician} /> : null}
        <ServiceOverviewCard service={details.service} bookingNumber={details.bookingNumber} createdAt={details.createdAt} />
        <FinalizedAddressCard address={details.address} />
        <FinalizedPricingCard pricing={details.pricing} />
        <AttachmentsSummary attachments={details.attachments} note={details.note} />
        <BookingActivity events={details.activity} />
        <BookingUpdatesCard capability={details.notifications} />
        <BookingDetailsActions
          onRefresh={() => query.refetch()} refreshing={query.isRefetching}
          onContactSupport={() => (navigation as unknown as { navigate: (name: string, params?: object) => void })
            .navigate("CreateSupportRequest", { source: "booking", bookingId })}
        />
      </View>
    </AppScreen>
  );
}
