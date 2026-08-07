import React, { useState } from "react";
import { View } from "react-native";
import { useBookingReviewController, bookingReviewLoadLabel } from "../booking-review/useBookingReviewController";
import { BotAssistantBubble, BotWorkingStep } from "../../components/bookingChat/BotPrimitives";
import { PhotosNotesTurn } from "../../components/bookingChat/PhotosNotesTurn";
import { PriceProviderCard } from "../../components/bookingChat/PriceProviderCard";
import { ConfirmCard } from "../../components/bookingChat/ConfirmCard";

export interface ReviewAndConfirmPhaseProps {
  draftId: string;
  onTrackBooking: (bookingId: string) => void;
}

/**
 * Address is resolved BEFORE this component ever mounts (see
 * BookingChatScreen -- it is conditionally rendered, not conditionally
 * hooked), so `useBookingReviewController`'s own load sequence
 * (checkServiceability -> resolvePriceEstimate -> matchAndPrice ->
 * confirmPriceChoice -> buildBookingSummary) always runs against a draft
 * that already has a real address/zipcode. This reuses that controller
 * completely unchanged -- only the rendering is the new dark chat shell,
 * every real API call and state machine is the same one Review already
 * used and had tested.
 */
export function ReviewAndConfirmPhase({ draftId, onTrackBooking }: ReviewAndConfirmPhaseProps) {
  const c = useBookingReviewController(draftId);
  const [photosDone, setPhotosDone] = useState(false);

  if (c.uiState === "loading" && c.loadStage) {
    return <BotWorkingStep label={bookingReviewLoadLabel(c.loadStage)} status="pending" />;
  }

  if (c.uiState === "offline" || c.uiState === "recoverable_error" || c.uiState === "blocked") {
    return (
      <BotAssistantBubble text={c.errorMessage ?? "Something went wrong while preparing your booking. Pull to retry from My Bookings, or try again."} />
    );
  }

  if (c.uiState === "confirmed" && c.confirmation) {
    return (
      <ConfirmCard
        bookingNumber={c.confirmation.bookingNumber}
        providerName={c.summary?.provider?.providerName ?? null}
        onTrackBooking={() => onTrackBooking(c.confirmation!.bookingId)}
      />
    );
  }

  if (!c.summary) return null;

  return (
    <View style={{ gap: 12 }}>
      {!photosDone ? (
        <PhotosNotesTurn
          photoUrls={c.summary.photoUrls}
          onAddPhoto={c.addPhoto}
          onRemovePhoto={c.removePhoto}
          onContinue={() => setPhotosDone(true)}
        />
      ) : (
        <PriceProviderCard
          summary={c.summary}
          confirming={c.uiState === "confirming"}
          onConfirm={c.confirm}
          confirmDisabledReason={c.eligibility.allowed ? null : "We can't confirm this request yet -- see the details above."}
        />
      )}
    </View>
  );
}
