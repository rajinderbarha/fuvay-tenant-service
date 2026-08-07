import { useCallback, useEffect, useRef, useState } from "react";
import { Keyboard } from "react-native";
import { AssistantEntryContext } from "../../domain/assistantEntry";
import { AssistantUiState, assertValidAssistantTransition, STALL_PRONE_STATES } from "../../domain/assistantUiState";
import { AssistantActivityStage } from "../../domain/assistantActivity";
import { QuestionFlowEnvelope } from "../../domain/questionEnvelope";
import { AssistantSession, AssistantMessage, AssistantLanguageOption } from "../../domain/assistantSession";

export type { AssistantLanguageOption };
import { CustomerId } from "../../domain/ids";
import { DomainError } from "../../domain/errors";
import * as assistantApi from "../../api/assistant/assistantApi";
import * as draftApi from "../../api/bookingDrafts/bookingDraftApi";
import * as questionFlowApi from "../../api/questionFlow/questionFlowApi";
import * as assistantBootstrapApi from "../../api/assistantBootstrap/assistantBootstrapApi";
import * as reviewApi from "../../api/bookingReview/bookingReviewApi";
import { parseAssistantSessionDto, adaptAssistantSession, parseSendMessageResponse, adaptSendMessageResult } from "../../api/adapters/assistantSession";
import { parseBookingDraftOrNullDto } from "../../api/adapters/bookingDraft";
import { parseQuestionFlowEnvelope, adaptQuestionFlowEnvelope } from "../../api/adapters/questionFlow";
import { saveAssistantPointer } from "../../storage/draft/assistantSessionPersistence";
import { logger } from "../../utils/logger";

const GUIDED_FALLBACK_DELAY_MS = 8000;

function scopeKeyFor(entry: AssistantEntryContext): string {
  return entry.source === "service_card" ? entry.categorySlug : "generic";
}

export interface AssistantOfferingOption {
  id: string;
  slug: string;
  name: string;
}

export interface AssistantOfferingChoice {
  categoryName: string;
  categorySlug: string;
  offerings: AssistantOfferingOption[];
}

/** The real, backend-resolved price for a draft whose questions are all
 * answered. Mirrors `price_snapshot` from POST /price-estimate. */
export interface AssistantPriceSnapshot {
  displayPrice: string | null;
  visitFee: number | null;
  requiresInspectionEstimate: boolean;
  customerMessage: string | null;
  pricingMode: string | null;
}

export interface AssistantControllerState {
  uiState: AssistantUiState;
  activityStage: AssistantActivityStage | null;
  session: AssistantSession | null;
  draftId: string | null;
  envelope: QuestionFlowEnvelope | null;
  messages: AssistantMessage[];
  errorMessage: string | null;
  fallbackOffered: boolean;
  /** Backend-first Booking Assistant bootstrap (Phase 1-4 of the
   * re-architecture): the real, zipcode-serviceable offering list for the
   * current category, present ONLY while the customer hasn't picked one
   * yet and no draft exists. Never populated from DeepSeek -- see
   * `HomeServiceChatbotBookingService.get_assistant_bootstrap`. */
  offeringChoice: AssistantOfferingChoice | null;
  /** CUSTOMER-ASSISTANT-UX-04 Part 1: the chatbot-language choice is the
   * FIRST interaction of every fresh request. Non-null only while that
   * choice is still pending -- the issue list is deliberately not loaded
   * until a language is picked, so the customer never sees booking
   * content in a language they haven't chosen. The options are entirely
   * backend-derived (`build_language_options`, ZIP-aware), never a
   * hardcoded client list. */
  languageChoice: AssistantLanguageOption[] | null;
  /** Real backend price once every question is answered; null before that. */
  priceSnapshot: AssistantPriceSnapshot | null;
}

export interface AssistantControllerActions {
  sendMessage: (text: string) => Promise<void>;
  interpretFreeText: (text: string) => Promise<void>;
  /** Free text typed BEFORE any offering is selected -- routed through the
   * constrained `OfferingInterpretationService`, never general DeepSeek
   * chat. Never creates a draft itself; a `match_option` result calls
   * `selectOffering` through the exact same path a tap uses. */
  interpretOfferingText: (text: string) => Promise<void>;
  /** Creates the canonical draft directly (no DeepSeek involved) and loads
   * its first real backend question. Accepts more than one real issue at
   * once (spec: "add multiple problem") -- the first is canonical for
   * job-type resolution, the rest are stored alongside it; issues
   * spanning different services are rejected by the backend. */
  selectOffering: (offerings: AssistantOfferingOption[]) => Promise<void>;
  submitAnswer: (questionId: string, optionId: string | null, value: string | null) => Promise<void>;
  changeLanguage: (code: string) => Promise<void>;
  /** The first interaction of a fresh request: persists the chatbot
   * language on the canonical session, then reveals the backend issue
   * list. Affects the chatbot conversation only, never app chrome. */
  chooseLanguage: (option: AssistantLanguageOption) => Promise<void>;
  continueWithGuidedFallback: () => void;
  cancelCurrentOperation: () => void;
  retry: () => void;
  /** Explicit "start again": discards the current conversation and
   * bootstraps a genuinely new request for the same service. The old
   * draft is never deleted, just no longer active. */
  restart: () => void;
}

/**
 * The single controller for the Booking Assistant screen -- owns the
 * explicit `AssistantUiState` machine, request-generation guarding
 * (spec: "Protect against late responses overwriting newer state"), and
 * every real backend call. No question ordering/validation logic lives
 * here; every question/answer decision is whatever the backend's own
 * envelope says (see api/questionFlow).
 */
export function useAssistantController(entryContext: AssistantEntryContext, customerId: CustomerId): AssistantControllerState & AssistantControllerActions {
  const scopeKey = scopeKeyFor(entryContext);
  const [uiState, setUiStateRaw] = useState<AssistantUiState>("bootstrapping");
  const [activityStage, setActivityStage] = useState<AssistantActivityStage | null>(null);
  const [session, setSession] = useState<AssistantSession | null>(null);
  const [draftId, setDraftId] = useState<string | null>(entryContext.existingDraftId);
  const [envelope, setEnvelope] = useState<QuestionFlowEnvelope | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fallbackOffered, setFallbackOffered] = useState(false);
  const [offeringChoice, setOfferingChoice] = useState<AssistantOfferingChoice | null>(null);
  const [languageChoice, setLanguageChoice] = useState<AssistantLanguageOption[] | null>(null);
  // Real, backend-resolved price for the current draft. Null until every
  // question is answered -- a price genuinely does not exist before that,
  // and a fabricated/placeholder one would be worse than none.
  const [priceSnapshot, setPriceSnapshot] = useState<AssistantPriceSnapshot | null>(null);
  // The bootstrap payload is fetched up front but held here until a
  // language is chosen, so picking a language does NOT cost a second
  // network round-trip before the issue list can appear.
  const pendingIssuesRef = useRef<{ categoryName: string; offerings: AssistantOfferingOption[] } | null>(null);
  /** Which preselected issue has already been auto-selected, so a
   * re-render cannot select it a second time. Cleared on scope reset. */
  const autoSelectedIssueRef = useRef<string | null>(null);
  // The chosen conversation language, mirrored into a ref so the
  // question-flow callbacks can read it without taking `session` as a
  // dependency (which would re-create them on every session update and
  // churn every consumer).
  const languageRef = useRef<string | null>(null);

  const generationRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const fallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const busyRef = useRef(false);

  const setUiState = useCallback((next: AssistantUiState) => {
    setUiStateRaw(prev => {
      assertValidAssistantTransition(prev, next);
      return next;
    });
  }, []);

  const isStale = useCallback((generation: number) => generation !== generationRef.current, []);

  function armFallbackTimer() {
    clearFallbackTimer();
    fallbackTimerRef.current = setTimeout(() => setFallbackOffered(true), GUIDED_FALLBACK_DELAY_MS);
  }
  function clearFallbackTimer() {
    if (fallbackTimerRef.current) clearTimeout(fallbackTimerRef.current);
    fallbackTimerRef.current = null;
  }

  // `sessionIdForPointer` is passed explicitly by every caller (their own
  // local variable, e.g. bootstrap's `resolvedSession.id`) rather than
  // read from the `session` state closure -- this function can run
  // synchronously within the SAME render pass as the `setSession(...)`
  // call that establishes it, before React has committed that state
  // update, so the closed-over `session` variable can still be null right
  // when it matters most (the very first bootstrap on a stale pointer).
  // Reading it from a real local variable instead avoids that stale-
  // closure race entirely.
  const refreshQuestionFlow = useCallback(async (currentDraftId: string, generation: number, sessionIdForPointer: string | null) => {
    setActivityStage("preparing_next_question");
    try {
      const raw = await questionFlowApi.getQuestionFlow(currentDraftId, languageRef.current, sessionIdForPointer);
      if (isStale(generation)) return;
      setEnvelope(adaptQuestionFlowEnvelope(parseQuestionFlowEnvelope(raw.data)));
    } catch (err) {
      // QF_JOB_TYPE_REQUIRED (422): a real, expected state for any draft
      // where no problem has been selected yet (e.g. a saved draft from
      // before a problem was picked, or one DeepSeek hasn't resolved a
      // problem for yet) -- QuestionFlowService fails closed here by
      // design (see question_flow_service.py _require_scope). This must
      // fall back to plain conversation mode, not surface as a hard error:
      // the customer can still talk to DeepSeek, which is what resolves
      // the problem/job type in the first place.
      if (isStale(generation)) return;
      if (err instanceof DomainError && err.telemetryMeta?.backendCode === "QF_JOB_TYPE_REQUIRED") {
        setEnvelope(null);
        return;
      }
      if (err instanceof DomainError && err.telemetryMeta?.backendCode === "QF_OFFERING_UNAVAILABLE") {
        // A locally-cached draft_id (from an AsyncStorage pointer saved in
        // an earlier session) points at an offering that's no longer
        // published, or has no real problem/issue-type wiring -- discard
        // it entirely, both in state and in the persisted pointer, so the
        // next auto-kickoff/message genuinely starts a fresh, bookable
        // draft instead of getting stuck resuming a dead one forever.
        setEnvelope(null);
        setDraftId(null);
        if (sessionIdForPointer) {
          await saveAssistantPointer(customerId, scopeKey, sessionIdForPointer, null).catch(() => {});
        }
        return;
      }
      throw err;
    }
  }, [isStale, customerId, scopeKey]);

  const bootstrap = useCallback(async () => {
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setFallbackOffered(false);
    setUiState("resolving_session");
    setActivityStage("understanding_request");
    armFallbackTimer();
    try {
      // Per explicit product decision: tapping a service always starts a
      // brand-new conversation, never resumes a previously-saved draft --
      // the AsyncStorage pointer/resume path (loadAssistantPointer,
      // getAssistantSession(pointer.sessionId), pointer.draftId) is no
      // longer read here at all. A fresh session is created every time.
      setActivityStage("opening_saved_booking");
      const raw = await assistantApi.createAssistantSession({
        categoryId: entryContext.categoryId ?? undefined,
        zipcode: entryContext.zipcode,
      });
      const resolvedSession = adaptAssistantSession(parseAssistantSessionDto(raw.data));
      if (isStale(generation)) return;
      setSession(resolvedSession);

      const resolvedDraftId = entryContext.existingDraftId ?? null;

      await saveAssistantPointer(customerId, scopeKey, resolvedSession.id, resolvedDraftId);
      if (isStale(generation)) return;
      setDraftId(resolvedDraftId);

      if (resolvedDraftId) {
        setUiState("loading_question");
        await refreshQuestionFlow(resolvedDraftId, generation, resolvedSession.id);
        if (isStale(generation)) return;
        setUiState("ready");
      } else if (entryContext.source === "service_card") {
        // Backend-first Booking Assistant (re-architecture): the FIRST
        // visible booking choice comes directly from the backend
        // bootstrap -- never a synthetic "I need help with X" DeepSeek
        // kickoff message, and never DeepSeek-chosen offerings.
        //
        // CUSTOMER-ASSISTANT-CHAT-02 (binding product decision): an
        // explicit tap on a service from Home ALWAYS starts a brand-new
        // request. The bootstrap's `resumable_draft` field is never read
        // here at all any more -- an earlier version surfaced it as a
        // "Continue your X request?" card, and a real regression let that
        // card keep rendering even after the customer had already moved
        // into issue selection/questions (nothing ever cleared it once
        // set), so it appeared underneath an active required question.
        // Removing the read entirely, not just the rendering, makes that
        // whole failure mode structurally impossible -- there is no
        // resumable-draft state left in this controller to leak.
        setActivityStage("checking_serviceability");
        const bootstrapRaw = await assistantBootstrapApi.getAssistantBootstrap(entryContext.categorySlug, entryContext.zipcode);
        if (isStale(generation)) return;
        const bootstrap = bootstrapRaw.data;

        // Event logging (dev-only, per explicit request) -- makes this
        // exact class of "why am I seeing old state" bug traceable: what
        // the bootstrap actually returned and what this screen decided to
        // do with it, every time a service is tapped.
        logger.info("assistant.bootstrap", {
          categorySlug: entryContext.categorySlug,
          zipcode: entryContext.zipcode,
          issueCount: bootstrap.issues.length,
          decision: "always_new_request",
        });

        // CUSTOMER-APP-KEYBOARD-01: issue selection is a tap-only stage --
        // a keyboard left open from whatever screen the customer was on
        // before (Chat, Review, a previous free-text question) must not
        // linger open over it, covering the lower issue options.
        Keyboard.dismiss();
        const categoryName = bootstrap.category.name ?? entryContext.categoryName;
        // CUSTOMER-ASSISTANT-UX-04 Part 1: language is the FIRST
        // interaction. The real, backend-owned issue list is fetched here
        // (one round-trip) but deliberately withheld until the customer
        // has chosen a language, so booking content never appears in a
        // language they didn't pick. Options come from the backend's own
        // ZIP-aware `build_language_options` -- never a hardcoded client
        // list, and never a "Regional"/"Automatic"/device-language entry.
        pendingIssuesRef.current = {
          categoryName,
          // "offerings" is the field name kept for wire/UI-prop
          // stability -- it carries the real, backend-owned ISSUE list
          // (assistant-bootstrap's `issues`), never bare offerings, per
          // the "Brand appears before any real issue selection" fix.
          offerings: bootstrap.issues.map(i => ({ id: i.id, slug: i.id, name: i.label })),
        };
        setOfferingChoice(null);
        setLanguageChoice(resolvedSession.languageOptions);
        setMessages([{
          id: `welcome-${resolvedSession.id}`, role: "assistant",
          content: `Hi! I'm your ${categoryName} booking assistant. Let's get this sorted for you.`,
          createdAt: null,
        }, {
          id: `language-prompt-${resolvedSession.id}`, role: "assistant",
          content: "Choose your preferred language", createdAt: null,
        }]);
        setUiState("ready");
      } else {
        // Bare tab tap, no service-card context -- general conversation
        // mode; the first customer message lets DeepSeek's backend tool
        // create a draft. Out of scope for the backend-first structured
        // booking re-architecture (that only applies once a category has
        // been chosen).
        setUiState("ready");
      }
      clearFallbackTimer();
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      setActivityStage(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId, scopeKey, entryContext, isStale, refreshQuestionFlow]);

  useEffect(() => {
    // Reset all per-conversation state before bootstrapping -- this
    // effect re-runs whenever `scopeKey` changes (a different category),
    // and the screen component itself is NOT unmounted/remounted between
    // category taps (same route, new params), so without this the old
    // category's session/messages/draftId/envelope stayed in state and
    // rendered until the new bootstrap happened to overwrite each piece
    // individually -- confirmed live: tapping a different service showed
    // the previous category's chat history.
    generationRef.current += 1; // invalidate any in-flight request from the previous scope
    // Reset straight to "bootstrapping" via the RAW setter, bypassing the
    // transition validator -- this is a deliberate full reset of a
    // previous, unrelated conversation, not a normal in-flow transition,
    // and most real uiStates (e.g. "ready", "submitting_answer") do NOT
    // allow a direct transition to "resolving_session" (what bootstrap()
    // sets next), so calling the guarded setter here throws synchronously
    // and crashes the app the moment a customer switches category mid-
    // conversation -- confirmed live (red crash screen).
    setUiStateRaw("bootstrapping");
    setSession(null);
    setDraftId(entryContext.existingDraftId);
    setEnvelope(null);
    setMessages([]);
    setOfferingChoice(null);
    setLanguageChoice(null);
    setPriceSnapshot(null);
    pendingIssuesRef.current = null;
    autoSelectedIssueRef.current = null;
    languageRef.current = null;
    setErrorMessage(null);
    setFallbackOffered(false);
    setActivityStage(null);
    bootstrap();
    return () => {
      generationRef.current += 1; // invalidate any in-flight request on unmount
      clearFallbackTimer();
      abortControllerRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeKey]);

  const sendMessage = useCallback(async (text: string) => {
    if (busyRef.current || !session) return;
    busyRef.current = true;
    const generation = ++generationRef.current;
    abortControllerRef.current = new AbortController();
    setErrorMessage(null);
    setUiState("assistant_processing");
    setActivityStage("understanding_request");
    armFallbackTimer();
    try {
      const raw = await assistantApi.sendAssistantMessage(session.id, text, abortControllerRef.current.signal);
      if (isStale(generation)) return;
      const result = adaptSendMessageResult(parseSendMessageResponse(raw.data));
      setSession(result.session);
      setMessages(prev => [...prev, { id: `local-${Date.now()}`, role: "user", content: text, createdAt: null },
        { id: `reply-${Date.now()}`, role: "assistant", content: result.reply, createdAt: null, quickReplies: result.quickReplies ?? undefined }]);

      // ALWAYS re-check for the current draft by session, on every turn --
      // not just when draftId was still null. Confirmed live: DeepSeek can
      // create a NEW draft (or resolve a problem on a draft that already
      // existed) on any turn, not only the first one. Gating this behind
      // `if (!draftId)` meant that once any draft id was ever set, later
      // turns' newer/updated drafts were silently never picked up -- the
      // question-flow envelope kept pointing at a stale draft forever,
      // even though the backend had a perfectly real question ready on
      // the current one.
      setActivityStage("loading_requirements");
      const draftRaw = await draftApi.getBookingDraftByAiSession(session.id);
      if (isStale(generation)) return;
      const draftDto = parseBookingDraftOrNullDto(draftRaw.data);
      if (draftDto) {
        if (draftDto.id !== draftId) {
          setDraftId(draftDto.id);
          await saveAssistantPointer(customerId, scopeKey, result.session.id, draftDto.id);
        }
        setUiState("refreshing_question_flow");
        await refreshQuestionFlow(draftDto.id, generation, result.session.id);
        if (isStale(generation)) return;
      }
      setUiState("ready");
      clearFallbackTimer();
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      busyRef.current = false;
      setActivityStage(null);
    }
  }, [session, draftId, customerId, scopeKey, isStale, refreshQuestionFlow]);

  const submitAnswer = useCallback(async (questionId: string, optionId: string | null, value: string | null) => {
    if (busyRef.current || !draftId) return;
    // The next question is very likely tap-only -- and even when it isn't,
    // the customer just finished this answer, so the keyboard (if a
    // free-text answer opened it) has done its job.
    Keyboard.dismiss();
    busyRef.current = true;
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setUiState("submitting_answer");
    setActivityStage("validating_answer");
    armFallbackTimer();
    try {
      const raw = await questionFlowApi.submitQuestionFlowAnswer(draftId, {
        questionId, optionId, value, expectedVersion: envelope?.questionFlowVersion,
        language: languageRef.current, sessionId: session?.id ?? null,
      });
      if (isStale(generation)) return;
      setUiState("refreshing_question_flow");
      setActivityStage("saving_progress");
      setEnvelope(adaptQuestionFlowEnvelope(parseQuestionFlowEnvelope(raw.data)));
      setUiState("ready");
      clearFallbackTimer();
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "CONFLICT_STALE_WORKFLOW") {
        // QF_STALE_QUESTION_FLOW_VERSION (409) -- refresh rather than retry
        // the same stale submission (spec: never resubmit blindly).
        setErrorMessage("Available choices were updated. Showing the latest question.");
        try {
          await refreshQuestionFlow(draftId, generation, session?.id ?? null);
          setUiState("ready");
        } catch {
          setUiState("recoverable_error");
        }
      } else if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      busyRef.current = false;
      setActivityStage(null);
    }
  }, [draftId, envelope, isStale, refreshQuestionFlow, session]);

  // Backend-first Booking Assistant: selects one or more real issues
  // (spec: "add multiple problem" -- a customer may report more than one
  // real problem on the same booking) and resolves the canonical draft +
  // first backend question through `select_issue`, the SAME endpoint a
  // resumed draft's issue was originally chosen through. DeepSeek is
  // never involved in this call at all; issues spanning genuinely
  // different services are rejected by the backend, never silently
  // merged or dropped.
  const selectOffering = useCallback(async (offerings: AssistantOfferingOption[]) => {
    if (busyRef.current || !offeringChoice || offerings.length === 0) return;
    Keyboard.dismiss();
    busyRef.current = true;
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setUiState("assistant_processing");
    setActivityStage("loading_requirements");
    armFallbackTimer();
    try {
      const [primary, ...rest] = offerings;
      const raw = await assistantBootstrapApi.selectAssistantBootstrapIssue(
        offeringChoice.categorySlug, entryContext.source === "service_card" ? entryContext.zipcode : null,
        primary.id, session?.id ?? null, rest.map(o => o.id), languageRef.current,
      );
      if (isStale(generation)) return;
      setOfferingChoice(null);
      setDraftId(raw.data.draft_id);
      if (session) {
        await saveAssistantPointer(customerId, scopeKey, session.id, raw.data.draft_id);
      }
      if (isStale(generation)) return;
      setEnvelope(adaptQuestionFlowEnvelope(raw.data.envelope));
      setUiState("ready");
      clearFallbackTimer();
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      busyRef.current = false;
      setActivityStage(null);
    }
  }, [session, offeringChoice, entryContext, customerId, scopeKey, isStale]);

  // Backend-first Booking Assistant: the customer's own free-text message
  // typed BEFORE any issue is selected. Routed through
  // `OfferingInterpretationService` -- DeepSeek is given only the real,
  // zipcode-serviceable issue list and can only match one of them; it
  // never creates a draft itself. A `match_option` result goes through
  // `selectOffering`, the exact same path a tap uses.
  const interpretOfferingText = useCallback(async (text: string) => {
    if (busyRef.current || !offeringChoice) return;
    busyRef.current = true;
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setUiState("assistant_processing");
    setActivityStage("understanding_request");
    armFallbackTimer();
    try {
      const raw = await assistantBootstrapApi.interpretOfferingSelectionText(
        offeringChoice.categorySlug, entryContext.source === "service_card" ? entryContext.zipcode : null,
        text, session?.id ?? null,
      );
      if (isStale(generation)) return;
      const { action, reply, matched_offering: matchedOffering, offerings } = raw.data;
      setOfferingChoice(prev => (prev ? { ...prev, offerings: offerings.map(o => ({ id: o.id, slug: o.id, name: o.name })) } : prev));
      setMessages(prev => [
        ...prev,
        { id: `local-${Date.now()}`, role: "user", content: text, createdAt: null },
        { id: `reply-${Date.now()}`, role: "assistant", content: reply, createdAt: null },
      ]);
      clearFallbackTimer();
      busyRef.current = false;
      setActivityStage(null);
      setUiState("ready");
      if (action === "match_option" && matchedOffering) {
        await selectOffering([{ id: matchedOffering.id, slug: matchedOffering.id, name: matchedOffering.name }]);
      }
      return;
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
      busyRef.current = false;
      setActivityStage(null);
    }
  }, [offeringChoice, entryContext, session, isStale, selectOffering]);

  // Backend-first-with-DeepSeek-on-demand: the customer's own free-text
  // message, sent ONLY while a canonical question is active (see
  // AssistantScreen's routing between this and `sendMessage`). Never
  // calls the general DeepSeek chat endpoint and never lets DeepSeek pick
  // the next question -- `QuestionInterpretationService` on the backend
  // either submits a validated option through the exact same canonical
  // path a tap uses, or returns a reply while the SAME question stays
  // active. The envelope in the response is always authoritative; nothing
  // here is inferred from `reply` text.
  const interpretFreeText = useCallback(async (text: string) => {
    if (busyRef.current || !draftId) return;
    busyRef.current = true;
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setUiState("assistant_processing");
    setActivityStage("understanding_request");
    armFallbackTimer();
    try {
      const raw = await questionFlowApi.interpretQuestionFlowText(draftId, text, session?.id ?? null);
      if (isStale(generation)) return;
      const { reply, envelope: nextEnvelope } = raw.data;
      setEnvelope(adaptQuestionFlowEnvelope(nextEnvelope));
      setMessages(prev => [
        ...prev,
        { id: `local-${Date.now()}`, role: "user", content: text, createdAt: null },
        { id: `reply-${Date.now()}`, role: "assistant", content: reply, createdAt: null },
      ]);
      setUiState("ready");
      clearFallbackTimer();
    } catch (err) {
      if (isStale(generation)) return;
      clearFallbackTimer();
      if (err instanceof DomainError && err.category === "NETWORK_UNAVAILABLE") {
        setUiState("offline");
      } else {
        setErrorMessage(err instanceof DomainError ? err.diagnostic : "Something went wrong.");
        setUiState("recoverable_error");
      }
    } finally {
      busyRef.current = false;
      setActivityStage(null);
    }
  }, [draftId, session, isStale]);

  const changeLanguage = useCallback(async (code: string) => {
    if (!session) return;
    const generation = generationRef.current;
    try {
      const raw = await assistantApi.setAssistantSessionLanguage(session.id, code);
      if (isStale(generation)) return;
      // Never resets draft/answers/progress -- confirmed server-side
      // (AIConversationService.set_session_language) and reflected here
      // by only replacing `session`, nothing else.
      setSession(adaptAssistantSession(parseAssistantSessionDto(raw.data)));
      languageRef.current = code;
      // Re-present the CURRENT unanswered question in the new language.
      // Answers, progress and draft state are untouched -- this only
      // re-fetches the same envelope with a different presentation
      // language, never restarts or reorders the booking.
      if (draftId) {
        await refreshQuestionFlow(draftId, generation, session.id);
      }
    } catch (err) {
      setErrorMessage(err instanceof DomainError ? err.diagnostic : "Couldn't change language.");
    }
  }, [session, draftId, isStale, refreshQuestionFlow]);

  // CUSTOMER-ASSISTANT-UX-04 Part 1/2: the customer's FIRST interaction in
  // every fresh request. Persists the choice on the canonical AI session
  // (the single existing store for chatbot language -- no duplicate
  // client-side language state), echoes it as a customer chat bubble, and
  // only THEN reveals the real backend issue list that bootstrap already
  // fetched. This affects the chatbot conversation only; the rest of the
  // app's UI language is untouched.
  const chooseLanguage = useCallback(async (option: AssistantLanguageOption) => {
    if (busyRef.current || !session) return;
    busyRef.current = true;
    const generation = ++generationRef.current;
    setErrorMessage(null);
    setLanguageChoice(null);
    // Set BEFORE the round-trip so the issue list / first question that
    // follow are already requested in the chosen language.
    languageRef.current = option.code;
    setMessages(prev => [
      ...prev,
      { id: `language-${option.code}-${Date.now()}`, role: "user", content: option.label, createdAt: null },
    ]);
    setUiState("assistant_processing");
    setActivityStage("understanding_request");
    try {
      const raw = await assistantApi.setAssistantSessionLanguage(session.id, option.code);
      if (isStale(generation)) return;
      setSession(adaptAssistantSession(parseAssistantSessionDto(raw.data)));
    } catch (err) {
      // A failed language write must NOT strand the customer before the
      // issue list -- the conversation still proceeds (in the previous
      // language), rather than dead-ending on a language round-trip.
      logger.info("assistant.language.persist_failed", {
        code: option.code,
        reason: err instanceof DomainError ? err.diagnostic : "unknown",
      });
    }
    if (isStale(generation)) {
      busyRef.current = false;
      setActivityStage(null);
      return;
    }
    const pending = pendingIssuesRef.current;
    if (pending) {
      setOfferingChoice({
        categoryName: pending.categoryName,
        categorySlug: entryContext.source === "service_card" ? entryContext.categorySlug : "",
        offerings: pending.offerings,
      });
      setMessages(prev => [
        ...prev,
        { id: `offering-prompt-${session.id}`, role: "assistant", content: "What do you need help with?", createdAt: null },
      ]);
    }
    busyRef.current = false;
    setActivityStage(null);
    setUiState("ready");
  }, [session, entryContext, isStale]);

  /**
   * Quick-issue entry from Home: the customer already named the problem
   * ("AC Not Cooling"), so showing them the same list again to pick it a
   * second time is a step with no content.
   *
   * This runs through `selectOffering` -- the exact path a tap takes --
   * rather than a parallel shortcut, so the draft, envelope and session
   * pointer are all created identically. It fires only once the real
   * backend issue list has arrived AND contains the id: a stale or
   * no-longer-serviceable id falls through to the normal picker instead
   * of erroring, and the ref guard stops a re-render from selecting
   * twice.
   */
  useEffect(() => {
    const issueId = entryContext.source === "service_card" ? entryContext.preselectedIssueId : null;
    if (!issueId || !offeringChoice) return;
    if (autoSelectedIssueRef.current === issueId) return;
    const match = offeringChoice.offerings.find(o => o.id === issueId);
    if (!match) return;
    autoSelectedIssueRef.current = issueId;
    void selectOffering([match]);
  }, [entryContext, offeringChoice, selectOffering]);

  const continueWithGuidedFallback = useCallback(() => {
    abortControllerRef.current?.abort();
    generationRef.current += 1; // discard whatever conversational request was in flight
    setFallbackOffered(false);
    setActivityStage("switching_to_guided");
    setUiState("guided_fallback");
    if (draftId) {
      setUiState("loading_question");
      refreshQuestionFlow(draftId, generationRef.current, session?.id ?? null)
        .then(() => setUiState("ready"))
        .catch(() => setUiState("recoverable_error"))
        .finally(() => setActivityStage(null));
    } else {
      setUiState("ready");
      setActivityStage(null);
    }
  }, [draftId, refreshQuestionFlow, session]);

  const cancelCurrentOperation = useCallback(() => {
    abortControllerRef.current?.abort();
    generationRef.current += 1;
    clearFallbackTimer();
    setFallbackOffered(false);
    setActivityStage(null);
    setUiState("ready");
  }, []);

  // Resolve the REAL price as soon as the backend says every question is
  // answered.
  //
  // Real bug fixed here: the Booking Assistant showed "Price pending"
  // forever, because price was only ever resolved on the Booking Review
  // screen. A customer who had answered every question still saw no price
  // on the screen where they were making the decision -- reported directly
  // ("price not populating after selection").
  //
  // Runs exactly once per draft (guarded by `pricedDraftRef`), never
  // fabricates a value, and stays silent on failure: an unresolved price
  // simply keeps the honest "Price pending" copy rather than showing an
  // error, since Booking Review re-resolves it authoritatively anyway.
  const pricedDraftRef = useRef<string | null>(null);
  const questionsComplete = !!envelope && envelope.currentQuestion === null && !!envelope.progress?.complete;
  useEffect(() => {
    if (!draftId || !questionsComplete) return;
    if (pricedDraftRef.current === draftId) return;
    pricedDraftRef.current = draftId;
    let cancelled = false;
    (async () => {
      try {
        // Serviceability must be resolved before a price can be computed --
        // same order Booking Review itself uses.
        await reviewApi.checkServiceability(draftId);
        if (cancelled) return;
        const raw = await reviewApi.resolvePriceEstimate(draftId);
        if (cancelled) return;
        const snap = raw.data.price_snapshot;
        if (!snap) return;
        setPriceSnapshot({
          displayPrice: (snap as Record<string, unknown>).display_price as string ?? null,
          visitFee: snap.visit_fee ?? null,
          requiresInspectionEstimate: !!snap.requires_inspection_estimate,
          customerMessage: snap.customer_message ?? null,
          pricingMode: (snap as Record<string, unknown>).pricing_mode as string ?? null,
        });
      } catch {
        // Deliberately silent -- see docstring above.
      }
    })();
    return () => { cancelled = true; };
  }, [draftId, questionsComplete]);

  const retry = useCallback(() => {
    bootstrap();
  }, [bootstrap]);

  // Explicit "start again" (header refresh action): discards the current
  // conversation entirely and bootstraps a genuinely NEW request for the
  // same service -- a fresh session, a fresh draft, an empty transcript.
  // The old draft is never deleted (it stays a real, findable historical
  // row); it is simply no longer the active one, exactly like the
  // always-new-request rule that governs an explicit service tap from
  // Home. Uses the RAW uiState setter for the same reason the scopeKey
  // reset effect does: this is a deliberate full reset, not a normal
  // in-flow transition, and most real states have no valid transition
  // into "resolving_session" (the guarded setter would throw).
  const restart = useCallback(() => {
    generationRef.current += 1; // invalidate anything in flight
    abortControllerRef.current?.abort();
    clearFallbackTimer();
    busyRef.current = false;
    Keyboard.dismiss();
    setUiStateRaw("bootstrapping");
    setSession(null);
    setDraftId(null);
    setEnvelope(null);
    setMessages([]);
    setOfferingChoice(null);
    setLanguageChoice(null);
    setPriceSnapshot(null);
    pendingIssuesRef.current = null;
    autoSelectedIssueRef.current = null;
    languageRef.current = null;
    setErrorMessage(null);
    setFallbackOffered(false);
    setActivityStage(null);
    bootstrap();
  }, [bootstrap]);

  return {
    uiState, activityStage, session, draftId, envelope, messages, errorMessage, fallbackOffered,
    offeringChoice, languageChoice, priceSnapshot,
    sendMessage, interpretFreeText, interpretOfferingText, selectOffering,
    submitAnswer, changeLanguage, chooseLanguage, continueWithGuidedFallback, cancelCurrentOperation, retry, restart,
  };
}

export { STALL_PRONE_STATES };
