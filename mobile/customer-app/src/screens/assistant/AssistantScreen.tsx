import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, FlatList, Keyboard, Platform, Pressable, KeyboardEvent } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState, ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { AssistantHeader } from "../../components/assistant/AssistantHeader";
import { AssistantContextStrip } from "../../components/assistant/AssistantContextStrip";
import { ChatBubble } from "../../components/assistant/ChatBubble";
import { QuestionCard } from "../../components/assistant/QuestionCard";
import { OfferingChoiceCard, OfferingChoiceOption } from "../../components/assistant/OfferingChoiceCard";
import { BookingSummary } from "../../components/assistant/BookingSummary";
import { AssistantComposer } from "../../components/assistant/AssistantComposer";
import { AppButton } from "../../components/AppButton";
import { CustomerTabsParamList, CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { createAssistantCardEntryContext } from "../../domain/assistantEntry";
import { AssistantMessage } from "../../domain/assistantSession";
import { useAssistantController } from "./useAssistantController";

type Route = RouteProp<CustomerTabsParamList, "Assistant">;

/**
 * CUSTOMER-ASSISTANT-CHAT-03: a single, strictly sequential feed -- one
 * WhatsApp-level chat, not two disconnected UIs glued together. Real
 * defect fixed here: chat messages (free-text Q&A, general conversation)
 * lived in one scrolling `FlatList`, while the canonical question/answer
 * state (the current `QuestionCard`, already-answered Q&A rows, the
 * issue/offering card) lived as separate, FIXED elements below that list
 * -- two independent "boxes" a customer had to visually reconcile
 * themselves. Confirmed live: typing a free-text answer made the
 * question+reply appear in the upper scrolling box while the actual
 * next question rendered in a completely separate lower box, "on top"
 * of / disconnected from what the customer had just typed. Every one of
 * these pieces is now a single discriminated item inside the SAME
 * inverted list, in true chronological order -- there is no longer a
 * second box for anything to appear in.
 */
type TranscriptEntry =
  | { id: string; kind: "message"; message: AssistantMessage }
  | { id: string; kind: "question" }
  | { id: string; kind: "offering" }
  | { id: string; kind: "language" }
  | { id: string; kind: "summary" };

/**
 * Composition root for the Booking Assistant. Owns no business logic
 * itself -- every state transition, request, and persistence decision
 * lives in useAssistantController; this file only maps controller state
 * to the Level-5 visual layout (spec section 9).
 */
export function AssistantScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { data: profile } = useCustomerProfileQuery();
  const { data: home } = useCustomerHomeQuery();

  const entryContext = useMemo(() => {
    if (route.params) return route.params;
    // Bare tab tap: no service-card context. Falls back to the customer's
    // resolved Home ZIP (same source Home itself uses) -- never a
    // fabricated or hardcoded location.
    return createAssistantCardEntryContext({ zipcode: home?.address?.zipcode ?? "" });
  }, [route.params, home?.address?.zipcode]);

  const hasZipcode = !!entryContext.zipcode;

  if (!profile) {
    return (
      <AppScreen>
        <LoadingState label="Loading your assistant" />
      </AppScreen>
    );
  }

  if (!hasZipcode) {
    return (
      <AppScreen>
        <EmptyState
          icon="location-outline"
          title="Choose your location first"
          message="Fuvay Assistant needs your service location to check what's available."
          actionLabel="Go to Home"
          onAction={() => navigation.navigate("Home" as never)}
        />
      </AppScreen>
    );
  }

  return (
    <AssistantConversation
      entryContext={entryContext}
      customerId={profile.id}
      onClose={() => {
        Keyboard.dismiss();
        navigation.navigate("Home" as never);
      }}
    />
  );
}

function AssistantConversation({
  entryContext, customerId, onClose,
}: {
  entryContext: ReturnType<typeof createAssistantCardEntryContext>;
  customerId: import("../../domain/ids").CustomerId;
  onClose: () => void;
}) {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const c = useAssistantController(entryContext, customerId);

  // A tapped tap-only answer's label, held only for the brief window
  // between the tap and the backend confirming it -- lets the option
  // instantly become a customer chat bubble and the option cards
  // disappear from the active area immediately, rather than waiting for
  // the round-trip (physical-device review: the old design left the
  // QuestionCard visible-but-greyed for that whole window instead of
  // reading like a real chat turn).
  const [pendingAnswerLabel, setPendingAnswerLabel] = useState<string | null>(null);

  // CUSTOMER-APP-KEYBOARD-01: a keyboard opened on a screen the customer
  // was on before this one (Chat, Review, an earlier free-text question)
  // does not dismiss itself just because a different screen mounted --
  // centralizing the dismissal here (screen focus/blur) rather than
  // scattering it across every option component covers every path back
  // into the Assistant, not just the ones this screen's own actions
  // already handle (selectOffering/submitAnswer in the controller).
  useEffect(() => {
    const unsubFocus = navigation.addListener("focus", () => Keyboard.dismiss());
    const unsubBlur = navigation.addListener("blur", () => Keyboard.dismiss());
    return () => {
      unsubFocus();
      unsubBlur();
    };
  }, [navigation]);

  // CUSTOMER-CHAT-UX-04: the composer stayed hidden behind the iOS keyboard
  // even with a KeyboardAvoidingView, because this screen is a TAB screen:
  // `KeyboardAvoidingView` measures its own frame against the WINDOW, but
  // the tab navigator's screen container does not shrink when the keyboard
  // opens, so its computed padding was consistently short by the tab-bar +
  // bottom-safe-area height and the composer stayed under the keyboard.
  // Measuring the real keyboard frame from the OS events and padding the
  // container by exactly (keyboardHeight - bottomInset) is deterministic,
  // needs no guessed header offset, and does not fight any other
  // keyboard-avoidance system (KeyboardAvoidingView is gone from this
  // screen entirely -- never two competing systems).
  const insets = useSafeAreaInsets();
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const onShow = Keyboard.addListener(showEvent, (e: KeyboardEvent) => setKeyboardHeight(e.endCoordinates.height));
    const onHide = Keyboard.addListener(hideEvent, () => setKeyboardHeight(0));
    return () => {
      onShow.remove();
      onHide.remove();
    };
  }, []);
  // The screen's SafeAreaView already reserves `insets.bottom`; adding the
  // full keyboard height on top of it would overshoot by exactly that much
  // and leave a visible gap above the keyboard.
  const keyboardPadding = keyboardHeight > 0 ? Math.max(keyboardHeight - insets.bottom, 0) : 0;

  const isProcessing = (
    c.uiState === "assistant_processing" || c.uiState === "submitting_answer" || c.uiState === "refreshing_question_flow"
  );
  // A short, honest label for what's actually happening right now -- never
  // a fabricated/rotating word unrelated to the real request in flight
  // (per feedback: the previous fixed Processing/Loading/Finding cycle
  // showed the same thing regardless of what the app was doing). Tied
  // directly to the controller's own real uiState, the same source of
  // truth the rest of the screen already reads.
  const processingLabel = (
    c.uiState === "submitting_answer" ? "Saving your answer"
      : c.uiState === "refreshing_question_flow" ? "Loading next question"
      : "Thinking"
  );

  // These are plain derived values (not hooks), so it's safe for them to
  // depend only on controller/local state -- but they're computed here,
  // ABOVE the early returns below, because the transcriptItems memo (a
  // real hook, which per React's rules must run unconditionally on every
  // render) needs them to build the single unified feed.
  const question = c.envelope?.currentQuestion ?? null;
  // A tap-only question's own options render only while nothing is
  // pending -- the instant a tap fires, the card disappears from the
  // active area (replaced by the optimistic customer bubble + typing
  // indicator in the transcript) rather than lingering greyed-out.
  const questionCardVisible = !!question && !pendingAnswerLabel;
  const tapOnlyQuestionActive = !!question && !question.acceptsFreeText;
  const progress = c.envelope?.progress;
  const questionsComplete = !!c.envelope && c.envelope.currentQuestion === null && !!progress?.complete;

  // Chat bubbles render newest-at-bottom, like WhatsApp: FlatList with
  // inverted=true expects its data reversed (index 0 = most recent). This
  // hook MUST run before any early return below (offline/error/blocked) --
  // React requires every hook to run in the same order on every render, and
  // a hook declared after a conditional return throws a hard "Rendered
  // fewer hooks than expected" crash the moment uiState transitions into
  // one of those early-return states.
  //
  // CUSTOMER-ASSISTANT-CHAT-03: every piece of the conversation -- chat
  // messages, the currently-active question/offering card, already-
  // answered questions, and the booking summary -- is now ONE ordered
  // array of `TranscriptEntry`, rendered by the SAME inverted FlatList.
  // There is no longer a second, fixed-position UI for any of these to
  // appear in: the active card is always the newest item (front of this
  // inverted array = visually at the very bottom, right above the
  // composer), immediately followed by the most recently answered
  // question, then older answered questions, then ordinary chat messages
  // -- exactly the order a real conversation happened in.
  // Real bug fixed here: chat messages (free-text Q&A replies) and
  // answered-question rows come from two independent backend-driven
  // arrays -- `c.messages` and `c.envelope.answeredQuestions` -- neither
  // of which shares a common ordering key with the other. Concatenating
  // "all answered questions" then "all messages" (as an earlier version
  // of this fix did) put every chat message ABOVE every answered
  // question regardless of when each actually happened -- confirmed live:
  // typing "Test" against Question 3 (after Brand and Capacity had
  // already been answered by tap) rendered the "Test"/clarification
  // exchange ABOVE Brand/Capacity, even though it happened chronologically
  // AFTER them. `seqFor` assigns each item a real, monotonically
  // increasing sequence number the FIRST time it's ever seen (kept in a
  // ref so it survives re-renders), so answered questions and chat
  // messages interleave in true chronological order no matter which
  // array either one came from.
  const seqCounterRef = useRef(0);
  const messageSeqRef = useRef<Map<string, number>>(new Map());
  const answeredSeqRef = useRef<Map<string, number>>(new Map());
  function seqFor(map: Map<string, number>, id: string): number {
    let seq = map.get(id);
    if (seq === undefined) {
      seq = seqCounterRef.current++;
      map.set(id, seq);
    }
    return seq;
  }

  const transcriptItems = useMemo<TranscriptEntry[]>(() => {
    const synthetic: TranscriptEntry[] = [];
    if (isProcessing) {
      synthetic.push({
        id: "typing-indicator", kind: "message",
        message: { id: "typing-indicator", role: "assistant", content: processingLabel, createdAt: null, isTyping: true },
      });
    }
    if (pendingAnswerLabel) {
      synthetic.push({
        id: "pending-answer", kind: "message",
        message: { id: "pending-answer", role: "user", content: pendingAnswerLabel, createdAt: null },
      });
    }
    // Exactly one active interaction at a time, in priority order:
    // issue/offering choice -> the current catalog question. Language
    // selection was removed -- the offering choice is now always the
    // first active card in a fresh request.
    const activeCard: TranscriptEntry[] = questionCardVisible
      ? [{ id: "active-question", kind: "question" }]
      : (c.offeringChoice && !pendingAnswerLabel ? [{ id: "active-offering", kind: "offering" }] : []);
    const summaryItem: TranscriptEntry[] = questionsComplete && c.draftId
      ? [{ id: "booking-summary", kind: "summary" }]
      : [];
    // CUSTOMER-CHAT-UX-03: a completed question/answer becomes normal chat
    // history -- an assistant bubble (the question) followed by a
    // customer bubble (the answer), exactly like a real messaging app --
    // rather than a small, faded, disabled-looking form card. Two
    // sequence numbers per answered question (assigned once, first-seen)
    // keep the question bubble immediately before its own answer bubble
    // without needing a fractional/tie-breaking scheme.
    const answered = (c.envelope?.answeredQuestions ?? []).flatMap(a => ([
      {
        entry: {
          id: `answered-q-${a.questionId}`, kind: "message" as const,
          message: { id: `answered-q-${a.questionId}`, role: "assistant" as const, content: a.questionLabel, createdAt: null },
        },
        seq: seqFor(answeredSeqRef.current, `${a.questionId}:q`),
      },
      {
        entry: {
          id: `answered-a-${a.questionId}`, kind: "message" as const,
          message: { id: `answered-a-${a.questionId}`, role: "user" as const, content: a.answerLabel, createdAt: null },
        },
        seq: seqFor(answeredSeqRef.current, `${a.questionId}:a`),
      },
    ]));
    const messages = c.messages.map(m => ({
      entry: { id: m.id, kind: "message" as const, message: m },
      seq: seqFor(messageSeqRef.current, m.id),
    }));
    // Newest-first (descending seq) for the inverted list -- true
    // chronological interleave, not two separately-ordered blocks.
    const historical = [...answered, ...messages].sort((a, b) => b.seq - a.seq).map(x => x.entry);
    return [...synthetic, ...summaryItem, ...activeCard, ...historical];
  }, [c.messages, c.envelope?.answeredQuestions, c.offeringChoice, c.draftId, questionCardVisible, questionsComplete, isProcessing, pendingAnswerLabel, processingLabel]);

  // Explicit scroll-to-newest after every transcript change (customer
  // selection appended, typing indicator appended, assistant response
  // appended, options finished laying out) -- `onContentSizeChange` fires
  // once the FlatList's content has actually re-measured, avoiding a race
  // against layout that a fixed delay would only paper over. For an
  // inverted list, offset 0 IS the newest/bottom-most position.
  const transcriptListRef = useRef<FlatList<TranscriptEntry>>(null);

  const title = entryContext.source === "service_card" ? `${entryContext.categoryName} Assistant` : "Fuvay Assistant";

  function handleContinueToReview() {
    if (!c.draftId || !c.session) return;
    Keyboard.dismiss();
    // AssistantScreen is a TAB screen inside `CustomerTabs`; "BookingReview"
    // is registered one level up, on the root stack (`CustomerAppNavigator`)
    // -- confirmed via routeTypes.ts/CustomerAppNavigator.tsx. Calling
    // `navigation.navigate(...)` directly on the tab navigator's own prop
    // relied on React Navigation's implicit upward route-name search, which
    // is exactly the kind of ambiguity Phase 6 (physical-device Booking
    // Review investigation) calls out as a plausible "missing nested
    // navigator" failure mode. Reaching the parent stack explicitly removes
    // that ambiguity and gives this call a real, checked type instead of
    // the previous untyped cast.
    const params = { draftId: c.draftId, aiSessionId: c.session.id };
    const parent = navigation.getParent<NativeStackNavigationProp<CustomerAppStackParamList>>();
    if (parent) {
      parent.navigate("BookingReview", params);
    } else {
      (navigation as { navigate: (name: string, params: unknown) => void }).navigate("BookingReview", params);
    }
  }

  if (c.uiState === "offline") {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Reconnect to continue -- your progress is saved." actionLabel="Try again" onAction={c.retry} />
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
    return (
      <AppScreen>
        <ErrorState title="This isn't available right now" message={c.errorMessage ?? undefined} />
      </AppScreen>
    );
  }

  // Single-active-question invariant, composer half: a tap-only question
  // (real backend options exist) must be answered exclusively via its
  // QuestionCard -- the composer never renders alongside it, so there is
  // never a second, competing way to answer the same interaction.
  // CUSTOMER-APP-KEYBOARD-01 / CUSTOMER-ASSISTANT-CHAT-02: the composer is
  // a genuinely free-text (or, absent any active tap-only interaction,
  // general chat) affordance -- it must never mount at all during a
  // tap-only stage (issue selection, a tap-only catalog question), not
  // merely be hidden while still focusable underneath. Picking an issue no
  // longer accepts typed text either (product decision superseding the
  // earlier "type instead of tap an offering" design -- confirmed via
  // physical-device report that a keyboard left open over the issue list
  // covered the lower options and had nothing tap-only about it).
  const composerAllowed = !c.offeringChoice && !tapOnlyQuestionActive;
  // The envelope carries no "already selected" field for the current
  // question (see domain/questionEnvelope.ts) -- a new question always
  // renders unselected until the customer taps an option and the answer
  // round-trips through submitAnswer/refreshQuestionFlow.
  const selectedIds: string[] = [];

  async function handleSelectOption(optionId: string) {
    if (!question) return;
    const option = question.options.find(o => o.id === optionId);
    setPendingAnswerLabel(option?.label ?? option?.id ?? optionId);
    try {
      await c.submitAnswer(question.questionId, optionId, null);
    } finally {
      setPendingAnswerLabel(null);
    }
  }

  // Backend-first Booking Assistant: tapping (or multi-selecting +
  // Continue on) one or more issues creates the canonical draft directly
  // -- no DeepSeek call at all. Same optimistic-bubble + hide-the-card
  // interaction pattern as a question tap, for a continuous chat feel.
  async function handleSelectOffering(options: OfferingChoiceOption[]) {
    setPendingAnswerLabel(options.map(o => o.name).join(" + "));
    try {
      await c.selectOffering(options);
    } finally {
      setPendingAnswerLabel(null);
    }
  }

  async function handleSend(text: string) {
    // CUSTOMER-CHAT-UX-03: real bug fixed here -- the composer is only
    // ever mounted for a genuine `free_text` question (no backend options
    // at all; see `composerAllowed`/`tapOnlyQuestionActive` -- an
    // option-based question always hides the composer entirely, tap-only).
    // Routing a raw free-text answer through `interpretFreeText`
    // (DeepSeek's constrained interpreter, meant for matching typed text
    // against a set of real OPTIONS) was structurally wrong for a
    // question that has no options to match against at all -- DeepSeek
    // had nothing valid to match "Test" against, so it always rejected it
    // ("I'm sorry, I didn't quite catch that...") and re-asked the exact
    // same question as a SECOND, separate chat message, alongside the
    // canonical QuestionCard still showing the same question -- a real,
    // confirmed duplicate. A genuine free-text answer now goes straight
    // to `submitAnswer` (the same canonical `QuestionFlowService.
    // submit_answer` path a tap uses), exactly like the backend's own
    // question-flow contract expects; DeepSeek is never consulted for it.
    //
    // Submit-dismisses-keyboard (WhatsApp-style): the customer just sent a
    // real message -- the keyboard has done its job for this turn, and
    // the next thing on screen (the typing indicator, then either a new
    // tap-only question or the same question staying active) shouldn't
    // have to fight a still-open keyboard for space.
    Keyboard.dismiss();
    if (question) {
      // Same optimistic-bubble pattern as a tap answer (handleSelectOption)
      // -- the typed text becomes a customer chat bubble immediately, and
      // the QuestionCard disappears from the active area right away
      // rather than lingering while the round-trip is in flight.
      setPendingAnswerLabel(text);
      try {
        await c.submitAnswer(question.questionId, null, text);
      } finally {
        setPendingAnswerLabel(null);
      }
    } else {
      await c.sendMessage(text);
    }
  }

  return (
    <AppScreen edges={["top", "bottom"]}>
      {/* WhatsApp layout: header / scrollable conversation / composer, with
          the composer always sitting directly on top of the keyboard.
          `paddingBottom` here is the real, OS-reported keyboard height
          (minus the safe-area inset the SafeAreaView already reserves), so
          the conversation genuinely shrinks and the composer rides up with
          the keyboard rather than being covered by it. */}
      <View style={{ flex: 1, paddingBottom: keyboardPadding }}>
        <View style={{ gap: theme.spacing.base, flex: 1 }}>
          <AssistantHeader title={title} onClose={onClose} onRestart={c.restart} />
          <AssistantContextStrip entryContext={entryContext} jobTypeLabel={null} />

          {c.uiState === "bootstrapping" || c.uiState === "resolving_session" ? (
            <LoadingState label="Opening your assistant" />
          ) : (
            <>
              {/* Processing renders inline as the newest transcript entry
                  (the typing-indicator synthetic message), never as a
                  top-of-screen status banner.

                  Real bug fixed here: this FlatList used to be wrapped in a
                  <Pressable> that dismissed the keyboard on tap. A Pressable
                  ancestor claims the touch responder, which STEALS the pan
                  gesture from the list underneath -- so the conversation
                  could not be scrolled at all once its content grew past one
                  screen (reported live: "not scrolling when booking summary
                  shows"). Tap-to-dismiss is not worth breaking scrolling:
                  the list's own `keyboardDismissMode` already gives
                  WhatsApp-style drag-to-dismiss, and every real action
                  (sending, answering, navigating) dismisses explicitly. */}
              <FlatList
                ref={transcriptListRef}
                style={{ flex: 1 }}
                // WhatsApp ordering: the conversation grows bottom-to-top --
                // the newest entry (the active question/offering card) sits
                // at the very BOTTOM, directly above the composer, and older
                // history scrolls up and away. `inverted` + a newest-first
                // data array is the standard RN way to get exactly that,
                // and it keeps the newest content pinned above the keyboard
                // when it opens. `justifyContent: flex-end` anchors a short
                // conversation to the bottom too, instead of floating it in
                // the middle of an otherwise empty screen.
                contentContainerStyle={{ flexGrow: 1, justifyContent: "flex-end", gap: theme.spacing.sm, paddingVertical: theme.spacing.sm }}
                data={transcriptItems}
                inverted
                keyExtractor={item => item.id}
                keyboardShouldPersistTaps="handled"
                // WhatsApp-style dismissal: dragging the conversation
                // closes the keyboard interactively (iOS) / on the first
                // drag frame (Android) -- never a competing gesture with
                // scrolling or with a bubble's own tap.
                keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
                onContentSizeChange={() => transcriptListRef.current?.scrollToOffset({ offset: 0, animated: true })}
                renderItem={({ item }) => {
                  switch (item.kind) {
                    case "message":
                      return (
                        <ChatBubble
                          message={item.message}
                          onQuickReply={handleSend}
                          quickRepliesDisabled={isProcessing}
                          // Single-active-question invariant: a canonical
                          // catalog question (rendered as its own item in
                          // this SAME list) owns the interaction the
                          // moment it exists -- any chat message's own
                          // quick-replies (e.g. a schedule preset
                          // DeepSeek attached earlier) must not render
                          // alongside it.
                          suppressQuickReplies={!!question}
                        />
                      );
                    case "question":
                      return (
                        <QuestionCard
                          question={question as NonNullable<typeof question>}
                          selectedOptionIds={selectedIds}
                          onSelectOption={handleSelectOption}
                          disabled={c.uiState === "submitting_answer"}
                        />
                      );
                    case "offering":
                      return c.offeringChoice ? (
                        <OfferingChoiceCard
                          options={c.offeringChoice.offerings}
                          onSubmit={handleSelectOffering}
                          disabled={isProcessing}
                          multiSelect
                        />
                      ) : null;
                    case "summary":
                      return <BookingSummary entryContext={entryContext} envelope={c.envelope} price={c.priceSnapshot} />;
                    default:
                      return null;
                  }
                }}
              />

              {questionsComplete ? (
                <AppButton label="Continue to review" onPress={handleContinueToReview} fullWidth />
              ) : composerAllowed ? (
                // Conditionally UNmounted, never merely hidden, for every
                // tap-only stage (issue selection, a tap-only catalog
                // question) -- see composerAllowed. A
                // hidden-but-still-focusable TextInput is exactly what let
                // a stray keyboard reopen or linger over those stages.
                <AssistantComposer disabled={isProcessing} onSend={handleSend} placeholder={question ? "Add details…" : "Type your answer"} />
              ) : null}
            </>
          )}
        </View>
      </View>
    </AppScreen>
  );
}
