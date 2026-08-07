import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { View, Text, FlatList, TextInput, Pressable, KeyboardAvoidingView, Platform, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { CustomerTabsParamList } from "../../navigation/routeTypes";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerHomeQuery } from "../../api/home/useCustomerHomeQuery";
import { createAssistantCardEntryContext } from "../../domain/assistantEntry";
import { useAssistantController } from "../assistant/useAssistantController";
import { useBookingChatAddress } from "./useBookingChatAddress";
import { ReviewAndConfirmPhase } from "./ReviewAndConfirmPhase";
import { resolveActivityLabel } from "../../domain/assistantActivity";
import { useBotColors } from "../../components/bookingChat/botTheme";
import {
  BotStageTracker, BotAssistantBubble, BotUserBubble, BotOptionChips, BotTypingDots,
  BotWorkingTrace, useWorkingTrace, BotPulseDot,
} from "../../components/bookingChat/BotPrimitives";
import { AddressTurn } from "../../components/bookingChat/AddressTurn";

type Route = RouteProp<CustomerTabsParamList, "Assistant">;

const STAGES = ["Understand", "Match technician", "Confirm & price", "Book"];

/**
 * Composition root for the merged booking chat. Same entry-context/profile
 * resolution as the old AssistantScreen (route params or Home's own ZIP,
 * never a fabricated location) -- only what happens once inside is new.
 */
export function BookingChatScreen() {
  const BOT = useBotColors();
  const navigation = useNavigation();
  const route = useRoute<Route>();
  const { data: profile } = useCustomerProfileQuery();
  const { data: home } = useCustomerHomeQuery();

  const entryContext = useMemo(() => {
    if (route.params) return route.params;
    return createAssistantCardEntryContext({ zipcode: home?.address?.zipcode ?? "" });
  }, [route.params, home?.address?.zipcode]);

  if (!profile) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
        <View
          accessibilityRole="progressbar"
          accessibilityLabel="Loading your assistant"
          style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 8 }}
        >
          <ActivityIndicator color={BOT.brand} size="large" />
          <Text style={{ color: BOT.textMuted, fontSize: 15 }}>Loading your assistant</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!entryContext.zipcode) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 12, paddingHorizontal: 32 }}>
          <Ionicons name="location-outline" size={32} color={BOT.textFaint} />
          <Text style={{ color: BOT.textPrimary, fontSize: 16, fontWeight: "700", textAlign: "center" }}>Choose your location first</Text>
          <Text style={{ color: BOT.textMuted, fontSize: 15, textAlign: "center" }}>
            Fuvay Assistant needs your service location to check what's available.
          </Text>
          <Pressable
            onPress={() => navigation.navigate("Home" as never)}
            accessibilityRole="button"
            accessibilityLabel="Go to Home"
            style={{ marginTop: 8, height: 40, paddingHorizontal: 20, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}
          >
            <Text style={{ color: BOT.bubbleOnBrand, fontSize: 15, fontWeight: "700" }}>Go to Home</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <BookingChatConversation
      entryContext={entryContext}
      customerId={profile.id}
      onClose={() => navigation.navigate("Home" as never)}
    />
  );
}

function BookingChatConversation({
  entryContext, customerId, onClose,
}: { entryContext: ReturnType<typeof createAssistantCardEntryContext>; customerId: import("../../domain/ids").CustomerId; onClose: () => void }) {
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

  // The composer is a real input only while a free-text question is
  // genuinely open and not already being submitted.
  const answerBusy = c.uiState === "submitting_answer" || c.uiState === "refreshing_question_flow";
  const freeTextActive = !!c.envelope?.currentQuestion?.acceptsFreeText && !questionsComplete && !traceBusy;
  const canSendAnswer = freeTextActive && answerDraft.trim().length > 0 && !answerBusy;

  function submitFreeText() {
    if (!canSendAnswer || !c.envelope?.currentQuestion) return;
    const text = answerDraft.trim();
    const questionId = c.envelope.currentQuestion.questionId;
    setAnswerDraft("");
    setLiveTraceQuestionId(questionId);
    c.submitAnswer(questionId, null, text);
  }

  return (
    // Bottom edge intentionally excluded -- the bottom tab bar already
    // supplies its own safe-area inset, so including it here left a blank
    // BOT.bg strip between the composer and the tab bar.
    <SafeAreaView edges={["top", "left", "right"]} style={{ flex: 1, backgroundColor: BOT.bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {/* Header */}
        <View style={{ paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: BOT.borderSubtle }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close" style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border }}>
              <Ionicons name="chevron-back" size={17} color={BOT.textTertiary} />
            </Pressable>
            <View style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}>
              <Ionicons name="sparkles" size={16} color={BOT.bubbleOnBrand} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ fontSize: 17, fontWeight: "700", color: BOT.textPrimary }}>Fuvay AI</Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <BotPulseDot color={booked ? BOT.success : BOT.brand} />
                <Text style={{ fontSize: 12, color: BOT.textMuted }}>{booked ? "Booking confirmed" : "Working on your booking"}</Text>
              </View>
            </View>
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

              {c.offeringChoice && !selectedIssueLabel && !traceBusy ? (
                <BotOptionChips
                  items={c.offeringChoice.offerings.map(o => o.name)}
                  selected={null}
                  onSelect={label => {
                    const offering = c.offeringChoice!.offerings.find(o => o.name === label);
                    if (!offering) return;
                    setSelectedIssueLabel(label);
                    c.selectOffering([offering]);
                  }}
                />
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
                  draftId={c.draftId}
                  onConfirmed={onBookingConfirmed}
                  onTrackBooking={bookingId => (navigation as unknown as { navigate: (name: string, params: unknown) => void })
                    .navigate("BookingDetails", { bookingId })}
                />
              ) : null}
            </View>
          )}
        />

        {/* Composer. Only rendered as a text box when a free-text question
            is genuinely awaiting an answer -- otherwise it is a plain
            status strip, so it never looks like an input the customer can
            type into when nothing would accept the text. */}
        <View style={{ paddingHorizontal: 16, paddingVertical: 14, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, backgroundColor: BOT.bgComposer }}>
          {freeTextActive ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
              <TextInput
                value={answerDraft}
                onChangeText={setAnswerDraft}
                onSubmitEditing={submitFreeText}
                editable={!answerBusy}
                returnKeyType="send"
                placeholder="Type your answer"
                placeholderTextColor={BOT.textTertiary}
                accessibilityLabel="Type your answer"
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
              <Ionicons name="sparkles" size={15} color={BOT.textTertiary} />
              <Text style={{ flex: 1, fontSize: 13, color: BOT.textTertiary }} numberOfLines={1}>
                {booked ? "Your booking is confirmed" : inReviewPhase ? "Fuvay AI is finishing your booking…" : "Choose an option above to continue"}
              </Text>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
