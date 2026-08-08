import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { useBookingReviewController, bookingReviewLoadLabel } from "../booking-review/useBookingReviewController";
import { BotAssistantBubble, BotWorkingTrace, useWorkingTrace, useObservedSequence } from "../../components/bookingChat/BotPrimitives";
import { SlotPickerCard } from "../../components/bookingChat/SlotPickerCard";
import { PhotosNotesTurn } from "../../components/bookingChat/PhotosNotesTurn";
import { ServiceChecklistCard } from "../../components/bookingChat/ServiceChecklistCard";
import { useServiceChecklist } from "./useServiceChecklist";
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
  /**
   * Reports the confirm phase (and the real details) UP to the screen.
   *
   * This component renders inside the chat transcript, so a `flex: 1` overlay
   * here can only ever fill its slot in the list -- which is why the
   * confirmation looked like another card instead of taking over. The screen
   * owns the full-bleed layer; this just tells it what to show.
   */
  onConfirmPhase?: (state: ConfirmPhaseState | null) => void;
  /**
   * Reports the ready-to-review state UP, so the screen can present it as a
   * full-screen sheet. Same reason as `onConfirmPhase`: this component renders
   * inside the chat transcript and cannot fill the screen from there, and the
   * final irreversible step should not compete with a scrolling chat log.
   */
  onReviewReady?: (state: ReviewReadyState | null) => void;
}

export interface ReviewReadyState {
  /** The summary the sheet renders. Carried in this state rather than read
   * separately by the screen, so the sheet can never show details from a
   * different render than the actions it was given. */
  summary: BookingReviewSummary;
  slotLabel: string | null;
  confirming: boolean;
  confirmDisabledReason: string | null;
  onConfirm: () => void;
  onEditSlot: () => void;
  onEditPhotos: () => void;
}

export interface ConfirmPhaseState {
  phase: "confirming" | "confirmed";
  bookingId: string | null;
  bookingNumber: string | null;
  providerName: string | null;
  slotLabel: string | null;
  amountLabel: string | null;
  feeCreditedAgainstWork: boolean;
}

/** "Today" / "Tomorrow" / "Sat 9 Aug" for a promised slot. Mirrors the slot
 * picker's wording so the confirmation repeats back exactly what was chosen. */
function slotDayLabel(dateIso: string, daysAhead: number): string {
  if (daysAhead === 0) return "Today";
  if (daysAhead === 1) return "Tomorrow";
  const date = new Date(`${dateIso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return dateIso;
  return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
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
export function ReviewAndConfirmPhase({
  draftId, onTrackBooking, onConfirmed, onConfirmPhase, onReviewReady,
}: ReviewAndConfirmPhaseProps) {
  const c = useBookingReviewController(draftId);
  const [slotDone, setSlotDone] = useState(false);
  const [checklistDone, setChecklistDone] = useState(false);
  const [photosDone, setPhotosDone] = useState(false);

  // What the technician will actually do. Loaded alongside the review rather
  // than blocking it: a service with nothing authored simply skips this turn.
  const checklist = useServiceChecklist(draftId);

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

  // Committing the booking takes over the WHOLE screen, which this component
  // cannot do from inside the chat transcript -- so the phase is reported up and
  // the screen renders the full-bleed layer. The phase comes from the REAL
  // controller state: it reaches "confirmed" only once the backend has returned
  // a booking number, so a slow call keeps showing progress and a failure can
  // never land on a success screen.
  //
  // EVERY HOOK BELONGS ABOVE THE EARLY RETURNS. This effect originally sat
  // further down, past `if (loading) return ...`, so it was skipped on a loading
  // render and reached on the next one -- React counts hooks per render and
  // threw "Rendered more hooks than during the previous render" the moment the
  // summary finished loading.
  const confirming = c.uiState === "confirming";
  const confirmActive = confirming || (c.uiState === "confirmed" && !!c.confirmation);
  const slotForConfirm = c.summary?.promisedSlot ?? null;
  const inspectionForConfirm = c.summary?.inspection ?? null;

  useEffect(() => {
    if (!onConfirmPhase) return;
    if (!confirmActive) {
      onConfirmPhase(null);
      return;
    }
    onConfirmPhase({
      phase: confirming ? "confirming" : "confirmed",
      bookingId: c.confirmation?.bookingId ?? null,
      bookingNumber: c.confirmation?.bookingNumber ?? null,
      providerName: c.summary?.provider?.providerName ?? null,
      slotLabel: slotForConfirm
        ? `${slotDayLabel(slotForConfirm.date, slotForConfirm.daysAhead)}, ${slotForConfirm.timeWindow}`
        : null,
      amountLabel: inspectionForConfirm ? formatMoney(inspectionForConfirm.visitFee) : null,
      // Asserted by the backend next to the billing rule that enforces it.
      feeCreditedAgainstWork: !!inspectionForConfirm?.visitFeePolicy?.creditedAgainstWork,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmActive, confirming, c.confirmation, slotForConfirm, inspectionForConfirm]);

  // Ready to review = summary loaded, all earlier turns done, not confirming.
  // Reported up so the screen can show the full-screen sheet.
  const reviewReady =
    !loading
    && c.uiState !== "offline" && c.uiState !== "recoverable_error" && c.uiState !== "blocked"
    && !confirmActive
    && !!c.summary
    && slotDone
    && (checklistDone || !checklist.checklist || checklist.checklist.totalPoints === 0)
    && photosDone;

  const summaryForReview = c.summary;
  useEffect(() => {
    if (!onReviewReady) return;
    if (!reviewReady || !summaryForReview) {
      onReviewReady(null);
      return;
    }
    const slot = summaryForReview.promisedSlot;
    onReviewReady({
      summary: summaryForReview,
      slotLabel: slot ? `${slotDayLabel(slot.date, slot.daysAhead)}, ${slot.timeWindow}` : null,
      confirming: c.uiState === "confirming",
      confirmDisabledReason: c.eligibility.allowed
        ? null
        : "We can't confirm this request yet -- see the details above.",
      onConfirm: c.confirm,
      onEditSlot: () => setSlotDone(false),
      onEditPhotos: () => setPhotosDone(false),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewReady, summaryForReview, c.uiState, c.eligibility.allowed]);

  // ── Conditional rendering only from here down: no hooks past this line ────

  if (loading) {
    return <BotWorkingTrace entries={trace} />;
  }

  if (c.uiState === "offline" || c.uiState === "recoverable_error" || c.uiState === "blocked") {
    return (
      <BotAssistantBubble text={c.errorMessage ?? "Something went wrong while preparing your booking. Pull to retry from My Bookings, or try again."} />
    );
  }

  // Nothing is rendered in the transcript for these phases -- the screen's
  // overlay is showing instead.
  if (confirmActive) return null;

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
          emergencySurchargeLabel={
            c.summary.emergencySurchargePreview
              ? formatMoney(c.summary.emergencySurchargePreview)
              : null
          }
          availableSlots={c.availableSlots}
          slotsLoading={c.slotsLoading}
          slotSelectionError={c.slotSelectionError}
          onLoadSlots={emergency => c.loadAvailableSlots(emergency)}
          onSelectSlot={(dateIso, timeWindow, emergency) => c.selectSlot(dateIso, timeWindow, emergency)}
          onContinue={() => setSlotDone(true)}
        />
      ) : !checklistDone && checklist.checklist && checklist.checklist.totalPoints > 0 ? (
        <ServiceChecklistCard
          checklist={checklist.checklist}
          onContinue={() => setChecklistDone(true)}
        />
      ) : !photosDone ? (
        <PhotosNotesTurn
          photoUrls={c.summary.photoUrls}
          onAddPhoto={c.addPhoto}
          onRemovePhoto={c.removePhoto}
          onContinue={() => setPhotosDone(true)}
        />
      ) : (
        // Nothing in the transcript: the screen is showing the full-screen
        // review sheet, reported up via onReviewReady.
        null
      )}
    </View>
  );
}
