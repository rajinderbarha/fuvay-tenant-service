import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { useBookingReviewController, bookingReviewLoadLabel } from "../booking-review/useBookingReviewController";
import { BotAssistantBubble, BotWorkingTrace, useWorkingTrace, useObservedSequence } from "../../components/bookingChat/BotPrimitives";
import { SlotPickerCard } from "../../components/bookingChat/SlotPickerCard";
import { PhotosNotesTurn } from "../../components/bookingChat/PhotosNotesTurn";
import { PriceProviderCard } from "../../components/bookingChat/PriceProviderCard";
import { FeeAssuranceCard } from "../../components/bookingChat/FeeAssuranceCard";
import { ConfirmCard } from "../../components/bookingChat/ConfirmCard";
import { formatMoney } from "../../domain/money";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";
import { BookingReviewSummary } from "../../domain/bookingReview";

export interface ReviewAndConfirmPhaseProps {
  draftId: string;
  onTrackBooking: (bookingId: string) => void;
  /** Fires once the booking is genuinely confirmed by the backend, so the
   * header's stage tracker can tick "Book" only when it has really
   * happened -- it previously went all-green as soon as the address
   * resolved, claiming a booking that did not exist yet. */
  onConfirmed?: () => void;
}

/** The one real price the slot picker shows alongside a time -- there is
 * no per-slot price anywhere in the backend, so this is the same amount
 * every slot costs, never a fabricated time-of-day figure. */
function priceLabelFor(summary: BookingReviewSummary): string | null {
  if (summary.inspection) return `${formatMoney(summary.inspection.visitFee)} inspection visit`;
  if (summary.priceState.kind === "valid") return formatMoney(summary.priceState.amount);
  return resolveServicePriceDisplay(summary.priceState).label;
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
 *
 * Three sequential turns once the summary is ready: pick a time (with the
 * real price shown alongside it) -> optional photos -> provider + confirm.
 */
export function ReviewAndConfirmPhase({ draftId, onTrackBooking, onConfirmed }: ReviewAndConfirmPhaseProps) {
  const c = useBookingReviewController(draftId);
  const [slotDone, setSlotDone] = useState(false);
  const [photosDone, setPhotosDone] = useState(false);

  const confirmed = c.uiState === "confirmed" && !!c.confirmation;
  useEffect(() => {
    if (confirmed) onConfirmed?.();
  }, [confirmed, onConfirmed]);

  // The five real load stages (checking details -> serviceability ->
  // pricing -> provider -> preparing review) accumulate into a visible
  // checklist. Each line settles only when the controller genuinely
  // advances, so the trace is a readout of real work, not a timed script.
  const loading = c.uiState === "loading";
  const observed = useObservedSequence(loading && c.loadStage ? bookingReviewLoadLabel(c.loadStage) : null);
  const trace = useWorkingTrace(observed, loading);

  if (loading) {
    return <BotWorkingTrace entries={trace} />;
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
      {/* Settled checklist stays on screen -- the customer can still see
          what was actually checked on their behalf. */}
      <BotWorkingTrace entries={trace} />
      {!slotDone ? (
        <SlotPickerCard
          promisedSlot={c.summary.promisedSlot}
          priceLabel={priceLabelFor(c.summary)}
          availableSlots={c.availableSlots}
          slotsLoading={c.slotsLoading}
          slotSelectionError={c.slotSelectionError}
          onLoadSlots={emergency => c.loadAvailableSlots(emergency)}
          onSelectSlot={(dateIso, timeWindow, emergency) => c.selectSlot(dateIso, timeWindow, emergency)}
          onContinue={() => setSlotDone(true)}
        />
      ) : !photosDone ? (
        <PhotosNotesTurn
          photoUrls={c.summary.photoUrls}
          onAddPhoto={c.addPhoto}
          onRemovePhoto={c.removePhoto}
          onContinue={() => setPhotosDone(true)}
        />
      ) : (
        <>
          {/* Money is settled BEFORE the Confirm button, never after it --
              the customer should have no open question about what they are
              agreeing to pay. */}
          <FeeAssuranceCard
            inspection={c.summary.inspection}
            emergencySurcharge={c.summary.isEmergency ? c.summary.emergencySurcharge : null}
          />
          <PriceProviderCard
            summary={c.summary}
            confirming={c.uiState === "confirming"}
            onConfirm={c.confirm}
            confirmDisabledReason={c.eligibility.allowed ? null : "We can't confirm this request yet -- see the details above."}
          />
        </>
      )}
    </View>
  );
}
