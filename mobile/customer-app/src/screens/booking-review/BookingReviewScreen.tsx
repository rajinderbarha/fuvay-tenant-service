import React, { useEffect } from "react";
import { ScrollView, View } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { AssistantActivity } from "../../components/assistant/AssistantActivity";
import { ReviewHeader } from "../../components/booking-review/ReviewHeader";
import { ReviewStatusStrip } from "../../components/booking-review/ReviewStatusStrip";
import { ServiceSummaryCard } from "../../components/booking-review/ServiceSummaryCard";
import { ServiceAddressCard } from "../../components/booking-review/ServiceAddressCard";
import { PricingReviewCard } from "../../components/booking-review/PricingReviewCard";
import { ProviderAssignmentCard } from "../../components/booking-review/ProviderAssignmentCard";
import { PromisedSlotCard } from "../../components/booking-review/PromisedSlotCard";
import { BookingPhotoAttachments } from "../../components/booking-review/BookingPhotoAttachments";
import { NextSteps } from "../../components/booking-review/NextSteps";
import { ConfirmationPanel } from "../../components/booking-review/ConfirmationPanel";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useBookingReviewController, bookingReviewLoadLabel } from "./useBookingReviewController";
import { CONFIRMATION_BLOCK_COPY, ConfirmationBlockReason } from "../../domain/confirmationEligibility";

type Route = RouteProp<CustomerAppStackParamList, "BookingReview">;

/**
 * Loading-sequence label → the real `AssistantActivityStage` closest in
 * meaning (spec section 3 explicitly reuses "the existing AssistantActivity
 * visual language" -- not a new component). Only the label text differs;
 * the animated shell, reduced-motion handling and stage-dot rendering are
 * unchanged from the Booking Assistant phase.
 */
function loadStageToActivityStage(stage: NonNullable<ReturnType<typeof useBookingReviewController>["loadStage"]>) {
  const map = {
    checking_details: "understanding_request",
    checking_serviceability: "checking_serviceability",
    // Was "validating_answer" ("Validating your answer...") -- wrong text
    // for a price-resolution request, a genuinely different operation.
    checking_pricing: "resolving_price",
    // Was "preparing_next_question" -- wrong text while matching a
    // provider/tenant, not loading a question.
    finding_provider: "finding_provider",
    // Was "saving_progress" -- wrong text while hydrating the review
    // summary, not saving an answer.
    preparing_review: "preparing_review",
  } as const;
  return map[stage];
}

export function BookingReviewScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { draftId } = route.params;
  const c = useBookingReviewController(draftId);

  // Real bug fixed here: this used to call `navigation.reset(...)` inline in
  // the render body (`if (uiState === "confirmed") { navigation.reset(...) }`).
  // Navigating is a state update on the NAVIGATOR, so doing it during this
  // component's render triggers React's "Cannot update a component while
  // rendering a different component" error -- which is exactly what the
  // Booking Confirmed screen showed. Navigation is a side effect and belongs
  // in an effect, which runs after the commit.
  const confirmedBookingId = c.uiState === "confirmed" ? c.confirmation?.bookingId ?? null : null;
  useEffect(() => {
    if (!confirmedBookingId) return;
    navigation.reset({
      index: 0,
      routes: [{ name: "BookingConfirmation", params: { bookingId: confirmedBookingId } }],
    } as never);
  }, [confirmedBookingId, navigation]);

  function goBackToAssistant() {
    navigation.goBack();
  }

  if (c.uiState === "offline") {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Reconnect to continue -- your draft is saved." actionLabel="Try again" onAction={c.retry} />
      </AppScreen>
    );
  }

  if (c.uiState === "recoverable_error") {
    return (
      <AppScreen>
        <ErrorState title="Something went wrong" message={c.errorMessage ?? undefined} actionLabel="Try again" onAction={c.retry} />
      </AppScreen>
    );
  }

  if (c.uiState === "blocked") {
    const reason = (c.blockedReason ?? "unknown") as ConfirmationBlockReason;
    // A pricing-configuration gap (invalid/missing/zero fixed price) is
    // recoverable in ways "back to assistant" alone doesn't cover -- the
    // customer may just want to try again a moment later, or pick a
    // different service entirely, or reach support. Every other blocked
    // reason keeps the single "Back to assistant" action unchanged.
    if (reason === "pricing_unavailable") {
      return (
        <AppScreen>
          <ErrorState
            title="Pricing is currently unavailable for this service"
            message={CONFIRMATION_BLOCK_COPY[reason]}
            actionLabel="Try again"
            onAction={c.retry}
            secondaryActions={[
              { label: "Choose another service", onPress: goBackToAssistant },
              { label: "Get support", onPress: () => navigation.navigate("Support" as never) },
            ]}
          />
        </AppScreen>
      );
    }
    return (
      <AppScreen>
        <ErrorState
          title="This isn't ready to review yet"
          message={CONFIRMATION_BLOCK_COPY[reason]}
          actionLabel="Back to assistant"
          onAction={goBackToAssistant}
        />
      </AppScreen>
    );
  }

  // The reset itself happens in the effect above; this render just yields
  // nothing while the navigator swaps the screen out.
  if (c.uiState === "confirmed" && c.confirmation) {
    return null;
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <ReviewHeader onBack={goBackToAssistant} onClose={goBackToAssistant} />

        {c.uiState === "loading" && c.loadStage ? (
          <AssistantActivity
            stage={loadStageToActivityStage(c.loadStage)}
            zipcode={c.summary?.address.zipcode ?? null}
            fallbackOffered={false}
            onContinueWithGuidedFallback={() => {}}
          />
        ) : null}

        {c.summary ? (
          <>
            <ReviewStatusStrip zipcode={c.summary.address.zipcode} />
            <ServiceSummaryCard summary={c.summary} onEditAnswers={goBackToAssistant} />
            <ServiceAddressCard address={c.summary.address} onChange={goBackToAssistant} />
            <PricingReviewCard priceState={c.summary.priceState} inspection={c.summary.inspection} bargainAvailable={c.summary.bargainAvailable} />
            <ProviderAssignmentCard provider={c.summary.provider} />

            {/* WHEN the service actually happens -- shown before the customer
                commits, so they decide on a real, capacity-checked promise
                rather than confirming blind and waiting for a callback. */}
            <PromisedSlotCard
              slot={c.summary.promisedSlot}
              slaMinutes={c.summary.serviceSlaMinutes}
              availableSlots={c.availableSlots}
              slotsLoading={c.slotsLoading}
              slotSelectionError={c.slotSelectionError}
              onOpenPicker={c.loadAvailableSlots}
              onSelectSlot={c.selectSlot}
            />
            {/* Replaces a read-only "N photos attached" summary whose only
                action was a link back to the assistant -- there was no way
                to actually attach a photo anywhere in the app. */}
            <BookingPhotoAttachments
              photoUrls={c.summary.photoUrls}
              onAddPhoto={c.addPhoto}
              onRemovePhoto={c.removePhoto}
            />
            <NextSteps />
            {c.uiState === "confirming" ? (
              <AssistantActivity
                stage="confirming_booking"
                zipcode={c.summary.address.zipcode}
                fallbackOffered={false}
                onContinueWithGuidedFallback={() => {}}
              />
            ) : null}
            <ConfirmationPanel
              eligibility={c.eligibility}
              confirming={c.uiState === "confirming"}
              onBackToAssistant={goBackToAssistant}
              onConfirm={c.confirm}
            />
          </>
        ) : null}
      </View>
    </AppScreen>
  );
}
