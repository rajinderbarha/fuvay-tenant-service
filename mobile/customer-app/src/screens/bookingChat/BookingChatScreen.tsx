import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { View, FlatList, TextInput, Pressable, KeyboardAvoidingView, Platform, ActivityIndicator, Alert, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation, useRoute, RouteProp, useFocusEffect } from "@react-navigation/native";
import { CustomerTabsParamList } from "../../navigation/routeTypes";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import {
  createAssistantCardEntryContext, createServiceCardEntryContext,
} from "../../domain/assistantEntry";
import type { AssistantEntryContext } from "../../domain/assistantEntry";
import { CategoryChoiceTurn } from "../../components/bookingChat/CategoryChoiceTurn";
import { useAssistantController, type AssistantOfferingOption } from "../assistant/useAssistantController";
import { useBookingChatAddress } from "./useBookingChatAddress";
import { ReviewAndConfirmPhase } from "./ReviewAndConfirmPhase";
import type { ConfirmPhaseState, ReviewReadyState } from "./ReviewAndConfirmPhase";
import { ReviewSheet } from "../../components/bookingChat/ReviewSheet";
import { BookingConfirmFlow } from "../../components/bookingChat/BookingConfirmFlow";
import { resolveActivityLabel } from "../../domain/assistantActivity";
import { useBotColors } from "../../components/bookingChat/botTheme";
import {
  BotStageTracker, BotAssistantBubble, BotUserBubble, BotOptionChips, BotTypingDots,
  BotWorkingTrace, useWorkingTrace, BotPulseDot, BotCard, BotPrimaryButton, BOT_GUTTER,
} from "../../components/bookingChat/BotPrimitives";
import { AddressTurn } from "../../components/bookingChat/AddressTurn";
import { useServiceLocationPreference } from "../../hooks/useServiceLocationPreference";
import { FuvayIcon } from "../../components/FuvayIcon";
import { BotText } from "../../components/bookingChat/BotText";

type Route = RouteProp<CustomerTabsParamList, "Assistant">;

const STAGES = ["Understand", "Match technician", "Confirm & price", "Book"];

/**
 * Composition root for the merged booking chat. Same entry-context/profile
 * resolution (route params or Home's own ZIP,
 * never a fabricated location) -- only what happens once inside is new.
 */
export function BookingChatScreen() {
  const BOT = useBotColors();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { data: profile } = useCustomerProfileQuery();
  const serviceLocation = useServiceLocationPreference();
  const { data: home, isPending: homePending } = useCustomerHomeQuery(serviceLocation.zipcode ?? undefined);

  /**
   * A category the customer picked HERE, when they opened the assistant from
   * the tab bar with no service in mind. Held in state rather than pushed as
   * route params so backing out of the conversation returns to this picker
   * instead of leaving the tab.
   */
  const [pickedCategory, setPickedCategory] = useState<AssistantEntryContext | null>(null);

  const entryContext = useMemo(() => {
    if (route.params) return route.params;
    if (pickedCategory) return pickedCategory;
    return createAssistantCardEntryContext({
      zipcode: serviceLocation.zipcode ?? home?.address?.zipcode ?? "",
    });
  }, [route.params, pickedCategory, serviceLocation.zipcode, home?.address?.zipcode]);

  const locationResolutionPending = !route.params
    && !pickedCategory
    && !home?.address?.zipcode
    && !serviceLocation.isLoaded;

  if (!profile || locationResolutionPending) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
        <View
          accessibilityRole="progressbar"
          accessibilityLabel="Loading your assistant"
          style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 8 }}
        >
          <ActivityIndicator color={BOT.brand} size="large" />
          <BotText style={{ color: BOT.textMuted, fontSize: 15 }}>Loading your assistant</BotText>
        </View>
      </SafeAreaView>
    );
  }

  if (!entryContext.zipcode) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 12, paddingHorizontal: 32 }}>
          <Ionicons name="location-outline" size={32} color={BOT.textFaint} />
          <BotText style={{ color: BOT.textPrimary, fontSize: 16, fontWeight: "700", textAlign: "center" }}>Choose your location first</BotText>
          <BotText style={{ color: BOT.textMuted, fontSize: 15, textAlign: "center" }}>
            Fuvay Assistant needs your service location to check what's available.
          </BotText>
          <Pressable
            onPress={() => navigation.navigate("Home" as never)}
            accessibilityRole="button"
            accessibilityLabel="Go to Home"
            style={{ marginTop: 8, height: 40, paddingHorizontal: 20, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}
          >
            <BotText style={{ color: BOT.bubbleOnBrand, fontSize: 15, fontWeight: "700" }}>Go to Home</BotText>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  /**
   * Opened from the tab with no service chosen: ask which one.
   *
   * The controller's category-less branch renders no turn, no options and no
   * usable composer, so mounting the conversation here would show an empty
   * chat. Choosing a category upgrades this to exactly the same entry context a
   * service card on Home produces.
   */
  if (entryContext.source === "assistant_card") {
    return (
      <SafeAreaView edges={["top", "left", "right"]} style={{ flex: 1, backgroundColor: BOT.bg }}>
        <AssistantIntroHeader locationLabel={home?.address?.city ?? entryContext.zipcode} />
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 32 }}
        >
          <CategoryChoiceTurn
            categories={home?.bookableCategories ?? []}
            serviceGroups={home?.bookableServiceGroups ?? []}
            loading={homePending}
            city={home?.address?.city ?? null}
            zipcode={entryContext.zipcode}
            onSelect={category => setPickedCategory(createServiceCardEntryContext({
              categoryId: category.categoryId,
              categoryName: category.name,
              // A category with no slug cannot be bootstrapped; the picker only
              // offers what Home offers, and Home drops slug-less categories
              // too -- so this fallback is never the path taken in practice.
              categorySlug: category.slug ?? "",
              zipcode: entryContext.zipcode,
            }))}
            onSelectGroup={group => setPickedCategory(createServiceCardEntryContext({
              categoryId: group.categoryId,
              categoryName: group.name,
              categorySlug: group.categorySlug,
              serviceGroupSlug: group.slug,
              zipcode: entryContext.zipcode,
            }))}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <BookingChatConversation
      entryContext={entryContext}
      customerId={profile.id}
      // Backing out of a conversation the customer started from the tab returns
      // to the service picker rather than throwing them over to Home.
      onClose={() => {
        if (pickedCategory && !route.params) {
          setPickedCategory(null);
          return;
        }
        navigation.navigate("Home" as never);
      }}
    />
  );
}

/** Same identity strip the conversation shows, so the picker reads as the
 * beginning of that conversation rather than a different screen. */
function AssistantIntroHeader({ locationLabel }: { locationLabel?: string | null }) {
  const BOT = useBotColors();
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: 12,
        paddingHorizontal: 20, paddingTop: 10, paddingBottom: 14,
        backgroundColor: BOT.surface,
        borderBottomWidth: 1, borderBottomColor: BOT.borderSubtle,
      }}
    >
      <View
        style={{
          width: 42, height: 42, borderRadius: 21, alignItems: "center",
          justifyContent: "center", backgroundColor: BOT.surfaceRaised,
          borderWidth: 1, borderColor: BOT.border,
        }}
      >
        <FuvayIcon size={28} accessibilityLabel="Fuvay booking assistant" />
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <BotText style={{ fontSize: 18, fontWeight: "800", color: BOT.textPrimary }}>Ask Fuvay</BotText>
        <BotText style={{ fontSize: 12, color: BOT.textMuted }}>Book confidently in a few simple steps</BotText>
      </View>
      {locationLabel ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 4, maxWidth: 104 }}>
          <Ionicons name="location-outline" size={14} color={BOT.textTertiary} />
          <BotText style={{ fontSize: 12, fontWeight: "600", color: BOT.textSecondary }} numberOfLines={1}>{locationLabel}</BotText>
        </View>
      ) : null}
    </View>
  );
}

/** The first actionable assistant turn. Problem identity comes from
 * assistant-bootstrap; IDs are the React/selection keys so repeated
 * labels cannot collide or select the wrong backend issue. */
function ProblemChoiceGrid({ items, onSelect }: {
  items: AssistantOfferingOption[];
  onSelect: (item: AssistantOfferingOption) => void;
}) {
  const BOT = useBotColors();
  const unique = Array.from(new Map(items.map(item => [item.id, item])).values());
  return (
    <View style={{ gap: 0, marginLeft: BOT_GUTTER, marginRight: 12, overflow: "hidden", borderRadius: 12, borderWidth: 1, borderColor: BOT.borderSubtle, backgroundColor: BOT.surface }}>
      {unique.map(item => {
        return (
          <Pressable
            key={item.id}
            onPress={() => onSelect(item)}
            accessibilityRole="button"
            accessibilityLabel={item.name}
            style={({ pressed }) => ({
              minHeight: 54, paddingHorizontal: 14, paddingVertical: 11,
              flexDirection: "row", alignItems: "center", gap: 10,
              borderBottomWidth: item.id === unique[unique.length - 1]?.id ? 0 : 1,
              borderBottomColor: BOT.borderSubtle,
              backgroundColor: pressed ? BOT.surfaceActive : BOT.surface,
              opacity: pressed ? 0.84 : 1,
            })}
          >
            <View style={{ width: 30, height: 30, borderRadius: 15, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceSunken }}>
              <Ionicons name="construct-outline" size={16} color={BOT.textSecondary} />
            </View>
            <BotText style={{ flex: 1, fontSize: 14, lineHeight: 19, fontWeight: "600", color: BOT.textPrimary }} numberOfLines={2}>{item.name}</BotText>
            <Ionicons name="chevron-forward" size={17} color={BOT.textFaint} />
          </Pressable>
        );
      })}
    </View>
  );
}

function BookingChatConversation({
  entryContext, customerId, onClose,
}: { entryContext: AssistantEntryContext; customerId: import("../../domain/ids").CustomerId; onClose: () => void }) {
  const BOT = useBotColors();
  const navigation = useNavigation();
  const c = useAssistantController(entryContext, customerId);
  const zipcode = entryContext.zipcode;

  const [selectedIssueLabel, setSelectedIssueLabel] = useState<string | null>(null);
  const [answerDraft, setAnswerDraft] = useState("");
  const listRef = useRef<FlatList>(null);

  const questionsComplete = !!c.envelope?.progress.complete;
  const addressPhaseActive = !!c.draftId && questionsComplete;
  const addr = useBookingChatAddress(c.draftId, zipcode);

  useEffect(() => {
    if (addressPhaseActive && addr.addresses === null && !addr.loading) {
      addr.loadAddresses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addressPhaseActive]);

  // Only a real, backend-confirmed booking completes the flow. This used to
  // be `!!addr.resolvedAddressId`, which ticked every stage green -- "Book"
  // included -- the moment an address was chosen, telling the customer they
  // were booked while they were still looking at the Confirm button.
  const [booked, setBooked] = useState(false);
  const inReviewPhase = !!addr.resolvedAddressId;
  // Stable identity: ReviewAndConfirmPhase fires this from an effect, so an
  // inline arrow would re-run that effect on every render.
  const onBookingConfirmed = useCallback(() => setBooked(true), []);

  // The confirm/confirmed screen is rendered HERE rather than inside the
  // transcript, so it genuinely fills the screen. Reported up by
  // ReviewAndConfirmPhase, which cannot escape its own slot in the list.
  const [confirmPhase, setConfirmPhase] = useState<ConfirmPhaseState | null>(null);
  const onConfirmPhase = useCallback((state: ConfirmPhaseState | null) => {
    setConfirmPhase(state);
  }, []);

  // The review sheet is also full-screen: confirming is the one irreversible
  // step and should not compete with a scrolling transcript and composer.
  const [reviewReady, setReviewReady] = useState<ReviewReadyState | null>(null);
  const onReviewReady = useCallback((state: ReviewReadyState | null) => {
    setReviewReady(state);
    // Leaving the review reopens an earlier turn, which clears the ready state.
    // Clearing the dismissal here is what lets the sheet come BACK once that
    // turn is finished again -- while the flag was sticky, finishing the slot
    // turn a second time rendered nothing at all: the transcript shows no card
    // (every turn is done) and the sheet was still suppressed, leaving the
    // customer on an empty chat with no way forward.
    if (!state) setReviewDismissed(false);
  }, []);
  // Lets the customer step back into the conversation without booking. Reopening
  // the slot turn is the honest "back": there is no earlier state to restore to
  // once the review has been reached.
  const [reviewDismissed, setReviewDismissed] = useState(false);

  /**
   * Begins a brand-new request.
   *
   * `c.restart()` resets the controller (session, draft, envelope, messages) but
   * knows nothing about this screen's own state, so the local turn/trace state
   * has to be cleared alongside it -- otherwise the fresh conversation inherits
   * the previous booking's confirmed overlay and answered-question traces.
   */
  const startNewBooking = useCallback(() => {
    setConfirmPhase(null);
    setReviewReady(null);
    setReviewDismissed(false);
    setBooked(false);
    setSelectedIssueLabel(null);
    setAnswerDraft("");
    setLiveTraceQuestionId(null);
    setTracesByQuestion({});
    c.restart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * A confirmed booking is TERMINAL, so RE-ENTERING the tab after one starts a
   * fresh conversation rather than showing a stale success screen.
   *
   * The refs are load-bearing. The first version listed `booked` as a dependency,
   * which made the focus effect re-run the instant `booked` flipped to true --
   * WHILE the screen was focused and the success screen was appearing. It reset
   * immediately, so confirming a booking restarted the chat and the customer
   * never saw the confirmation or its Track / Book-another / Done actions at all.
   *
   * Reading state through refs with an EMPTY dependency list means this runs only
   * on real focus and blur. `leftSinceBooking` is set on blur, so a reset happens
   * only after the customer has genuinely navigated away and come back.
   */
  const bookedRef = useRef(false);
  const leftSinceBooking = useRef(false);
  useEffect(() => { bookedRef.current = booked; }, [booked]);

  const startNewBookingRef = useRef(startNewBooking);
  useEffect(() => { startNewBookingRef.current = startNewBooking; }, [startNewBooking]);

  useFocusEffect(
    useCallback(() => {
      if (bookedRef.current && leftSinceBooking.current) {
        leftSinceBooking.current = false;
        startNewBookingRef.current();
      }
      return () => {
        // Cleanup runs on blur: remember that we left AFTER a booking, so the
        // next focus is a genuine return rather than the confirmation render.
        if (bookedRef.current) leftSinceBooking.current = true;
      };
    }, []),
  );

  // The full running task list for the current operation. The controller
  // records every stage it genuinely passed through (activityTrace), so
  // steps that resolve in the same React batch are still shown instead of
  // collapsing into one flash. Keyed on the live question so each question
  // gets its own trace rather than one list growing all conversation.
  const traceLabels = useMemo(
    () => c.activityTrace.map(stage => resolveActivityLabel(stage, zipcode)),
    [c.activityTrace, zipcode],
  );
  const trace = useWorkingTrace(traceLabels, c.activityStage !== null);

  // The next turn waits for the working steps to finish playing, so the
  // customer sees what was done before being asked the next thing --
  // options never pop in underneath a still-running trace.
  const traceBusy = trace.some(e => e.status === "pending");

  // Which question the running trace belongs to, and the finished trace of
  // every question answered before it. Without this, past questions lose
  // their steps and the whole transcript's worth of work piles up in one
  // block at the bottom instead of sitting with the question that caused it.
  const [liveTraceQuestionId, setLiveTraceQuestionId] = useState<string | null>(null);
  const [tracesByQuestion, setTracesByQuestion] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (!liveTraceQuestionId || traceLabels.length === 0) return;
    setTracesByQuestion(prev => ({ ...prev, [liveTraceQuestionId]: traceLabels }));
  }, [liveTraceQuestionId, traceLabels]);

  // Auto-scroll is handled by the list's onContentSizeChange (below), which
  // fires on every real growth. A second state-keyed scroll effect here
  // would fight it and make the list jitter.

  // Stages: 0 Understand · 1 Match technician · 2 Confirm & price · 3 Book.
  const activeStageIndex = booked ? 3 : !c.draftId || !questionsComplete ? 0 : !inReviewPhase ? 1 : 2;

  const answerBusy =
    c.uiState === "submitting_answer"
    || c.uiState === "refreshing_question_flow"
    || c.uiState === "assistant_processing";

  /**
   * Where a typed message goes. Three genuinely different destinations, which is
   * why this is resolved once here rather than branched inside the send handler:
   *
   *  - "answer"    a question with NO options: the text IS the answer, so it goes
   *                straight down the canonical submit path. DeepSeek is not
   *                consulted -- there is nothing to match it against, and an
   *                earlier version that did ask rejected every answer and
   *                re-asked the same question.
   *  - "interpret" a question WITH options: DeepSeek matches the words against
   *                those real options and either submits the canonical one or
   *                replies asking again, with the same question still active. It
   *                can never invent an option or choose the next question.
   *  - "issue"     no draft yet, still choosing the problem: the same constrained
   *                matching against the real backend issue list.
   *
   * This is the connection that was missing. Both interpreters existed, were
   * reachable and worked; the live screen simply never called either, so typing
   * was only possible on free-text questions and DeepSeek was never involved in a
   * booking at all.
   */
  const currentQuestion = c.envelope?.currentQuestion ?? null;
  const composerTarget: "answer" | "interpret" | "issue" | null =
    traceBusy ? null
      : currentQuestion && !questionsComplete
        ? ((currentQuestion.options?.length ?? 0) > 0 ? "interpret" : "answer")
        : c.offeringChoice && !c.draftId ? "issue"
          : null;
  const composerActive = composerTarget !== null;
  /** Says what typing will do here. "Type your answer" over the issue picker
   * asked for an answer to a question that had not been asked yet. */
  const composerPlaceholder =
    composerTarget === "issue" ? "Describe the problem"
      : composerTarget === "interpret" ? "Type or tap an option above"
        : "Type your answer";
  const canSendAnswer = composerActive && answerDraft.trim().length > 0 && !answerBusy;

  function confirmRestart() {
    Alert.alert(
      "Start over?",
      "This clears your answers and begins a new request. Your current draft will not be booked.",
      [
        { text: "Keep going", style: "cancel" },
        { text: "Start over", style: "destructive", onPress: startNewBooking },
      ],
    );
  }

  function submitFreeText() {
    if (!canSendAnswer) return;
    const text = answerDraft.trim();
    setAnswerDraft("");

    if (composerTarget === "issue") {
      c.interpretOfferingText(text);
      return;
    }
    if (!currentQuestion) return;
    setLiveTraceQuestionId(currentQuestion.questionId);
    if (composerTarget === "interpret") {
      // Constrained matching against this question's own options. The response
      // carries the authoritative envelope, so nothing here infers what to show
      // next from the reply text.
      c.interpretFreeText(text);
      return;
    }
    c.submitAnswer(currentQuestion.questionId, null, text);
  }

  return (
    // Bottom edge intentionally excluded -- the bottom tab bar already
    // supplies its own safe-area inset, so including it here left a blank
    // BOT.bg strip between the composer and the tab bar.
    // Outer plain View so the full-screen overlays below can sit OUTSIDE the
    // SafeAreaView's padding. Inside it, an absolutely-positioned overlay
    // inherits the host's inset handling, which is how the review sheet's header
    // ended up under the status bar. Each overlay now applies its own insets.
    <View style={{ flex: 1, backgroundColor: BOT.bg }}>
    <SafeAreaView edges={["top", "left", "right"]} style={{ flex: 1, backgroundColor: BOT.bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {/* Header */}
        <View
          style={{
            paddingHorizontal: 16,
            paddingTop: 10,
            paddingBottom: 12,
            backgroundColor: BOT.surface,
            borderBottomWidth: 1,
            borderBottomColor: BOT.borderSubtle,
          }}
        >
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close" style={{ width: 36, height: 40, alignItems: "flex-start", justifyContent: "center" }}>
              <Ionicons name="chevron-back" size={19} color={BOT.textSecondary} />
            </Pressable>
            <View style={{ width: 40, height: 40, borderRadius: 10, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border }}>
              <FuvayIcon size={27} accessibilityLabel="Fuvay booking assistant" />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <BotText style={{ fontSize: 10, fontWeight: "800", letterSpacing: 1.1, color: BOT.textTertiary }}>GUIDED BOOKING</BotText>
              <BotText style={{ fontSize: 18, lineHeight: 21, fontWeight: "800", color: BOT.textPrimary }}>Ask Fuvay</BotText>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <BotPulseDot color={booked ? BOT.success : BOT.brand} />
                <BotText style={{ fontSize: 12, color: BOT.textMuted }} numberOfLines={1}>
                  {booked ? "Booking confirmed" : `${entryContext.categoryName ?? "Service"} booking`}
                </BotText>
              </View>
            </View>

            {/* Start over. Deliberately NOT a silent reload: it abandons the
                current draft and begins a fresh conversation, so it asks first
                -- a customer who has answered eight questions should not lose
                them to a mis-tap. Hidden once booked, when there is nothing left
                to restart. */}
            {!booked ? (
              <Pressable
                onPress={confirmRestart}
                accessibilityRole="button"
                accessibilityLabel="Start over"
                hitSlop={8}
                style={{
                  width: 40, height: 40, borderRadius: 10,
                  alignItems: "center", justifyContent: "center",
                  backgroundColor: BOT.surfaceSunken,
                }}
              >
                <Ionicons name="refresh" size={17} color={BOT.textSecondary} />
              </Pressable>
            ) : null}
          </View>
          <BotStageTracker stages={STAGES} activeIndex={activeStageIndex} allDone={booked} />
        </View>

        {/* Transcript */}
        <FlatList
          ref={listRef}
          style={{ flex: 1 }}
          // Content-size driven, so EVERY growth scrolls -- a newly revealed
          // working step, a new bubble, a card mounting -- without needing a
          // state key for each one.
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 20, gap: 12 }}
          data={[0]}
          keyExtractor={() => "content"}
          renderItem={() => (
            <View style={{ gap: 12 }}>
              {/* 1. Issue selection */}
              {c.messages.map(m => (
                m.role === "user" ? <BotUserBubble key={m.id} text={m.content} /> : <BotAssistantBubble key={m.id} text={m.content} />
              ))}

              {(c.uiState === "bootstrapping" || c.uiState === "resolving_session") ? <BotTypingDots /> : null}

              {/* The controller's error, which this screen never rendered.
               *
               * Real bug this fixes: `errorMessage` was set on every failure path --
               * a failed bootstrap, a rejected answer, a dead session -- and NOTHING
               * displayed it. The typing dots stopped and the conversation simply
               * ended: nothing after the animated text, no reason, no retry. A silent
               * failure is the one outcome a booking flow cannot afford, because the
               * customer's only remaining move is to assume the app is broken. */}
              {/* A notice is not a failure: the flow recovered, and this explains why the
                  question changed. Rendered as a quiet line rather than the alert card
                  below -- a red box with "Try again" over a flow that just worked is
                  how a working assistant looks broken. */}
              {c.notice ? (
                <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 6, paddingHorizontal: 4 }}>
                  <Ionicons name="information-circle-outline" size={14} color={BOT.textMuted} style={{ marginTop: 1 }} />
                  <BotText style={{ flex: 1, fontSize: 12, color: BOT.textMuted }}>{c.notice}</BotText>
                </View>
              ) : null}

              {c.errorMessage ? (
                <BotCard>
                  <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 8 }}>
                    <Ionicons name="alert-circle" size={16} color={BOT.danger} style={{ marginTop: 2 }} />
                    <BotText style={{ flex: 1, fontSize: 13, color: BOT.textPrimary }}>{c.errorMessage}</BotText>
                  </View>
                  {/* Retry only. Starting over already has its own control in the
                      header, and a second one with the same label here would be two
                      different affordances answering to one name. */}
                  <View style={{ marginTop: 12 }}>
                    <BotPrimaryButton label="Try again" onPress={() => c.retry()} />
                  </View>
                </BotCard>
              ) : null}

              {c.offeringChoice && !selectedIssueLabel && !traceBusy ? (
                c.offeringChoice.offerings.length > 0 ? (
                  <ProblemChoiceGrid
                    items={c.offeringChoice.offerings}
                    onSelect={offering => {
                      setSelectedIssueLabel(offering.name);
                      c.selectOffering([offering]);
                    }}
                  />
                ) : (
                  /* The issue list came back EMPTY.
                   *
                   * Real bug this fixes: the bot greeted the customer, asked "What do
                   * you need help with?", and then rendered a chip row with no chips --
                   * a dead screen with no explanation and no way forward. A category can
                   * genuinely have nothing bookable at a given ZIP, so this has to say
                   * so and offer the two things that can actually change the answer.
                   *
                   * It does NOT fall back to another category's issues or to a generic
                   * "describe your problem" box, because the assistant's later steps
                   * (pricing, matching) are scoped to a real issue at a real ZIP. */
                  <BotCard>
                    <BotText style={{ fontSize: 15, fontWeight: "600", color: BOT.textPrimary }}>
                      Nothing to book here yet
                    </BotText>
                    <BotText style={{ fontSize: 13, color: BOT.textMuted, marginTop: 4 }}>
                      {`No ${c.offeringChoice.categoryName} problems are available in ${entryContext.zipcode} right now.`}
                    </BotText>
                    <View style={{ marginTop: 12 }}>
                      <BotPrimaryButton label="Choose another service" onPress={() => navigation.goBack()} />
                    </View>
                  </BotCard>
                )
              ) : null}

              {/* 2. Question loop -- answered history, then the live question */}
              {/* Each question keeps the steps that ran for IT, directly
                  below its answer -- so work stays attached to the question
                  that caused it instead of piling up in one block. */}
              {c.envelope?.answeredQuestions.map(a => (
                <View key={a.questionId} style={{ gap: 8 }}>
                  <BotAssistantBubble text={a.questionLabel} />
                  <BotUserBubble text={a.answerLabel} />
                  {a.questionId === liveTraceQuestionId ? (
                    <BotWorkingTrace entries={trace} />
                  ) : tracesByQuestion[a.questionId] ? (
                    <BotWorkingTrace
                      entries={tracesByQuestion[a.questionId].map(label => ({ label, status: "done" as const }))}
                    />
                  ) : null}
                </View>
              ))}

              {/* Work that belongs to no question in the history yet --
                  bootstrap, picking the issue, or the brief moment before
                  the answered question lands -- still shows in sequence
                  here, so a running trace is never rendered nowhere. */}
              {liveTraceQuestionId === null
                || !c.envelope?.answeredQuestions.some(a => a.questionId === liveTraceQuestionId)
                ? <BotWorkingTrace entries={trace} />
                : null}

              {c.envelope?.currentQuestion && !questionsComplete && !traceBusy ? (
                <View style={{ gap: 8 }}>
                  <BotAssistantBubble text={c.envelope.currentQuestion.text} />
                  {/* A free-text question is answered in the composer at the
                      bottom -- one real input, rather than a second one
                      inline competing with it. */}
                  {c.envelope.currentQuestion.acceptsFreeText ? null : (
                    <BotOptionChips
                      items={c.envelope.currentQuestion.options.map(o => o.label ?? "").filter(Boolean)}
                      selected={null}
                      onSelect={label => {
                        const opt = c.envelope!.currentQuestion!.options.find(o => o.label === label);
                        if (!opt) return;
                        const questionId = c.envelope!.currentQuestion!.questionId;
                        setLiveTraceQuestionId(questionId);
                        c.submitAnswer(questionId, opt.id, null);
                      }}
                    />
                  )}
                </View>
              ) : null}

              {/* 3. Address */}
              {addressPhaseActive && !addr.resolvedAddressId && !traceBusy ? (
                <AddressTurn
                  zipcode={zipcode}
                  addresses={addr.addresses}
                  loading={addr.loading}
                  submitting={addr.submitting}
                  error={addr.error}
                  onPickExisting={addr.pickExisting}
                  onCreateNew={addr.createNew}
                />
              ) : null}

              {/* 4. Price, photos, confirm -- reuses the real, already-tested
                  Review controller wholesale; only mounted once address is
                  resolved so its serviceability check never runs early. */}
              {addr.resolvedAddressId && c.draftId ? (
                <ReviewAndConfirmPhase
                  key={c.draftId}
                  draftId={c.draftId}
                  onConfirmed={onBookingConfirmed}
                  onConfirmPhase={onConfirmPhase}
                  onReviewReady={onReviewReady}
                  onTrackBooking={bookingId => (navigation as unknown as { navigate: (name: string, params: unknown) => void })
                    .navigate("BookingDetails", { bookingId })}
                />
              ) : null}
            </View>
          )}
        />

        {/* Composer. A real input whenever something would genuinely accept the
            text -- a question (with or without options) or the issue choice --
            and a plain status strip otherwise, so it never invites typing that
            nothing would read. */}
        <View style={{ paddingHorizontal: 16, paddingVertical: 14, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, backgroundColor: BOT.bgComposer }}>
          {composerActive ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
              <TextInput
                value={answerDraft}
                onChangeText={setAnswerDraft}
                onSubmitEditing={submitFreeText}
                editable={!answerBusy}
                returnKeyType="send"
                placeholder={composerPlaceholder}
                placeholderTextColor={BOT.textTertiary}
                accessibilityLabel={composerPlaceholder}
                style={{
                  flex: 1, minHeight: 48, borderRadius: 24, paddingHorizontal: 18, paddingVertical: 12,
                  backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border,
                  color: BOT.textPrimary, fontSize: 15,
                }}
              />
              <Pressable
                onPress={submitFreeText}
                disabled={!canSendAnswer}
                accessibilityRole="button"
                accessibilityLabel="Send answer"
                accessibilityState={{ disabled: !canSendAnswer }}
                style={{
                  width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center",
                  backgroundColor: canSendAnswer ? BOT.brand : BOT.surfaceRaised,
                }}
              >
                <Ionicons name="send" size={18} color={canSendAnswer ? BOT.bubbleOnBrand : BOT.textDim} />
              </Pressable>
            </View>
          ) : (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 4, minHeight: 24 }}>
              <FuvayIcon size={16} accessibilityLabel="Fuvay assistant" />
              <BotText style={{ flex: 1, fontSize: 13, color: BOT.textTertiary }} numberOfLines={1}>
                {booked
                  ? "Your booking is confirmed"
                  : inReviewPhase
                    ? "Fuvay AI is finishing your booking…"
                    : "Choose an option above to continue"}
              </BotText>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>

      {/* Full-screen review sheet. Rendered here, not in the transcript, so it
          genuinely fills the screen; dismissing returns to the conversation. */}
      {reviewReady && !confirmPhase && !reviewDismissed ? (
        <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
          <ReviewSheet
            summary={reviewReady.summary}
            slotLabel={reviewReady.slotLabel}
            confirming={reviewReady.confirming}
            confirmDisabledReason={reviewReady.confirmDisabledReason}
            onConfirm={reviewReady.onConfirm}
            onEditSlot={() => { setReviewDismissed(true); reviewReady.onEditSlot(); }}
            onEditPhotos={() => { setReviewDismissed(true); reviewReady.onEditPhotos(); }}
            onClose={() => { setReviewDismissed(true); reviewReady.onEditSlot(); }}
          />
        </View>
      ) : null}

      {/* Full-bleed confirm/confirmed layer. Absolutely positioned over the
          transcript AND the composer so nothing of the chat shows through --
          this is the whole point of it not living in the list. */}
      {confirmPhase ? (
        <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
          <BookingConfirmFlow
            phase={confirmPhase.phase}
            bookingNumber={confirmPhase.bookingNumber}
            providerName={confirmPhase.providerName}
            slotLabel={confirmPhase.slotLabel}
            amountLabel={confirmPhase.amountLabel}
            feeCreditedAgainstWork={confirmPhase.feeCreditedAgainstWork}
            onTrackBooking={() => {
              if (confirmPhase.bookingId) {
                (navigation as unknown as { navigate: (n: string, p: unknown) => void })
                  .navigate("BookingDetails", { bookingId: confirmPhase.bookingId });
              }
            }}
            onDone={onClose}
            onBookAnother={startNewBooking}
          />
        </View>
      ) : null}
    </View>
  );
}
