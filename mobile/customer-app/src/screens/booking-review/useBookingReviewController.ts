import {
  addPhotoToBookingDraft,
  removePhotoFromBookingDraft,
  type PickedPhoto,
} from "../../api/bookingPhotos/bookingPhotoApi";
import { useCallback, useEffect, useRef, useState } from "react";
import * as reviewApi from "../../api/bookingReview/bookingReviewApi";
import * as confirmApi from "../../api/bookingConfirmation/bookingConfirmationApi";
import * as questionFlowApi from "../../api/questionFlow/questionFlowApi";
import { parseQuestionFlowEnvelope, adaptQuestionFlowEnvelope } from "../../api/adapters/questionFlow";
import { parseDraftDto, parseBuildBookingSummaryResponse, adaptBookingReviewSummary, adaptBookingConfirmationResult } from "../../api/adapters/bookingReview";
import { BookingReviewSummary } from "../../domain/bookingReview";
import { BookingConfirmationResult } from "../../domain/bookingConfirmation";
import { resolveConfirmationEligibility, ConfirmationEligibility } from "../../domain/confirmationEligibility";
import { DomainError } from "../../domain/errors";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../../api/idempotency/idempotencyStore";

export type BookingReviewLoadStage =
  | "checking_details" | "checking_serviceability" | "checking_pricing" | "finding_provider" | "preparing_review";

export type BookingReviewUiState =
  | "loading" | "ready" | "blocked" | "offline" | "recoverable_error" | "confirming" | "confirmed";

const LOAD_LABELS: Record<BookingReviewLoadStage, string> = {
  checking_details: "Checking your booking details…",
  checking_serviceability: "Confirming service availability…",
  checking_pricing: "Checking backend pricing…",
  finding_provider: "Finding an eligible professional…",
  preparing_review: "Preparing your review…",
};

export function bookingReviewLoadLabel(stage: BookingReviewLoadStage): string {
  return LOAD_LABELS[stage];
}

export interface BookingReviewControllerState {
  uiState: BookingReviewUiState;
  loadStage: BookingReviewLoadStage | null;
  summary: BookingReviewSummary | null;
  eligibility: ConfirmationEligibility;
  errorMessage: string | null;
  blockedReason: string | null;
  confirmation: BookingConfirmationResult | null;
}

export interface BookingReviewControllerActions {
  retry: () => void;
  confirm: () => Promise<void>;
  /** Attach a photo of the problem to this draft. Lives here rather than in
   * the component because every draft mutation goes through the controller
   * -- the screen only picks the file. Resolves to the draft's new photo
   * list, or throws so the caller can surface a retry. */
  addPhoto: (photo: PickedPhoto) => Promise<void>;
  removePhoto: (photoUrl: string) => Promise<void>;
}

/**
 * Owns the entire load → revalidate → match-and-price → review →
 * idempotent-confirm sequence (spec sections 3/7/8). No screen component
 * calls a booking-review API function directly -- every state transition
 * and every mutation lives here.
 */
export function useBookingReviewController(draftId: string): BookingReviewControllerState & BookingReviewControllerActions {
  const [uiState, setUiState] = useState<BookingReviewUiState>("loading");
  const [loadStage, setLoadStage] = useState<BookingReviewLoadStage | null>("checking_details");
  const [summary, setSummary] = useState<BookingReviewSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<BookingConfirmationResult | null>(null);

  const generationRef = useRef(0);
  const busyRef = useRef(false);

  const load = useCallback(async () => {
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setBlockedReason(null);
    setUiState("loading");
    try {
      setLoadStage("checking_details");
      const envelopeRaw = await questionFlowApi.getQuestionFlow(draftId);
      if (generation !== generationRef.current) return;
      const envelope = adaptQuestionFlowEnvelope(parseQuestionFlowEnvelope(envelopeRaw.data));
      if (!envelope.progress.complete) {
        setBlockedReason("draft_incomplete");
        setUiState("blocked");
        return;
      }

      setLoadStage("checking_serviceability");
      const serviceability = await reviewApi.checkServiceability(draftId);
      if (generation !== generationRef.current) return;
      if (!serviceability.data.serviceable) {
        setBlockedReason("unserviceable");
        setUiState("blocked");
        return;
      }

      setLoadStage("checking_pricing");
      await reviewApi.resolvePriceEstimate(draftId);
      if (generation !== generationRef.current) return;

      setLoadStage("finding_provider");
      let matchResult;
      try {
        matchResult = await reviewApi.matchAndPrice(draftId);
      } catch (err) {
        if (generation !== generationRef.current) return;
        // `PRICE_OPTIONS_UNAVAILABLE` (raised by match_provider_and_price
        // when a fixed-price offering has no valid, positive tenant price
        // configured) is a genuinely different, more specific blocker than
        // "no eligible provider" -- conflating them previously showed the
        // wrong recovery copy ("No eligible professional is available")
        // for what is actually a pricing-configuration gap, not a coverage
        // gap. Distinguish by the real backend error code rather than
        // guessing from HTTP status alone.
        const backendCode = err instanceof DomainError ? err.telemetryMeta?.backendCode : undefined;
        setBlockedReason(backendCode === "PRICE_OPTIONS_UNAVAILABLE" ? "pricing_unavailable" : "no_provider");
        setUiState("blocked");
        return;
      }
      if (generation !== generationRef.current) return;

      // Auto-resolve the single-value 'standard' tier when bargaining is
      // unavailable -- the only path this phase drives (mission
      // statement: no bargaining UI this phase). A bargain-available
      // draft is left unresolved and surfaces as pricing_unavailable.
      if (!matchResult.data.bargain_available && matchResult.data.standard_price != null) {
        await reviewApi.confirmPriceChoice(draftId, "standard");
        if (generation !== generationRef.current) return;
      }

      setLoadStage("preparing_review");
      const [draftRaw, summaryRaw] = await Promise.all([
        reviewApi.getDraft(draftId),
        reviewApi.buildBookingSummary(draftId),
      ]);
      if (generation !== generationRef.current) return;

      const draftDto = parseDraftDto(draftRaw.data);
      const summaryDto = parseBuildBookingSummaryResponse(summaryRaw.data).booking_summary;
      const adapted = adaptBookingReviewSummary(draftDto, summaryDto);
      setSummary(adapted);
      setUiState("ready");
    } catch (err) {
      if (generation !== generationRef.current) return;
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      if (generation === generationRef.current) setLoadStage(null);
    }
  }, [draftId]);

  useEffect(() => {
    load();
    return () => { generationRef.current += 1; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const eligibility = summary
    ? resolveConfirmationEligibility({
        questionsComplete: true,
        hasAddress: !!summary.address.city,
        serviceable: summary.address.serviceable,
        hasSelectedProvider: !!summary.provider,
        priceState: summary.priceState,
        bargainAvailable: summary.bargainAvailable,
        readyForConfirmation: summary.readyForConfirmation,
        requestInFlight: uiState === "confirming",
      })
    : { allowed: false as const, reason: "unknown" as const };

  const confirm = useCallback(async () => {
    if (busyRef.current || !eligibility.allowed) return;
    busyRef.current = true;
    const generation = generationRef.current;
    setUiState("confirming");
    setErrorMessage(null);
    const idempotencyKey = await getOrCreateIdempotencyKey(`booking-confirm:${draftId}`);
    try {
      const raw = await confirmApi.confirmDraft(draftId, idempotencyKey);
      if (generation !== generationRef.current) return;
      const result = adaptBookingConfirmationResult(raw.data);
      await clearIdempotencyKey(`booking-confirm:${draftId}`);
      setConfirmation(result);
      setUiState("confirmed");
    } catch (err) {
      if (generation !== generationRef.current) return;
      // Timeout/network-uncertain outcome: reconcile by refreshing the
      // draft/review state rather than assuming failure -- the server may
      // already have completed the booking (spec section 8/9). The SAME
      // idempotency key is kept (not cleared) so a retry is safe.
      if (err instanceof DomainError && (err.category === "TIMEOUT" || err.category === "NETWORK_UNAVAILABLE")) {
        setErrorMessage("We couldn't confirm your connection. Checking your booking status…");
        await load();
        return;
      }
      if (err instanceof DomainError && err.category === "CONFLICT_STALE_WORKFLOW") {
        setErrorMessage("Some details changed since you opened this review. Refreshing…");
        await load();
        return;
      }
      setErrorMessage(err instanceof DomainError ? err.diagnostic : "We couldn't confirm your request.");
      setUiState("recoverable_error");
    } finally {
      busyRef.current = false;
    }
  }, [draftId, eligibility, load]);

  /** Both photo mutations return the server's authoritative list, so the
   * summary is updated from that rather than from a local guess -- the
   * backend enforces the max-photo cap and could reject what we sent. */
  const applyPhotoUrls = useCallback((photoUrls: string[]) => {
    setSummary(prev => (prev ? { ...prev, photoUrls, photoCount: photoUrls.length } : prev));
  }, []);

  const addPhoto = useCallback(async (photo: PickedPhoto) => {
    const result = await addPhotoToBookingDraft(draftId, photo);
    applyPhotoUrls(result.data.photo_urls);
  }, [draftId, applyPhotoUrls]);

  const removePhoto = useCallback(async (photoUrl: string) => {
    const result = await removePhotoFromBookingDraft(draftId, photoUrl);
    applyPhotoUrls(result.data.photo_urls);
  }, [draftId, applyPhotoUrls]);

  return {
    uiState, loadStage, summary, eligibility, errorMessage, blockedReason, confirmation,
    retry: load, confirm, addPhoto, removePhoto,
  };
}
