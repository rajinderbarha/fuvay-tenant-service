import React, { useEffect, useMemo, useRef, useState } from "react";
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

  const flowDone = !!addr.resolvedAddressId; // review phase mounts and owns everything past this

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

  // Auto-scroll to the newest turn as the conversation grows -- every state
  // change below (message count, a new question, address/price turns
  // mounting) reshapes the single content item, so this covers all of them
  // without needing a per-turn scroll call.
  const scrollCue = [
    c.messages.length, c.envelope?.answeredQuestions.length ?? 0, !!c.envelope?.currentQuestion,
    c.activityStage, c.uiState, addressPhaseActive, addr.resolvedAddressId, trace.length,
  ].join("|");
  useEffect(() => {
    const timer = setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
    return () => clearTimeout(timer);
  }, [scrollCue]);

  const activeStageIndex = !c.draftId ? 0 : !questionsComplete ? 0 : !addr.resolvedAddressId ? 1 : 2;

  // The composer is a real input only while a free-text question is
  // genuinely open and not already being submitted.
  const answerBusy = c.uiState === "submitting_answer" || c.uiState === "refreshing_question_flow";
  const freeTextActive = !!c.envelope?.currentQuestion?.acceptsFreeText && !questionsComplete && !traceBusy;
  const canSendAnswer = freeTextActive && answerDraft.trim().length > 0 && !answerBusy;

  function submitFreeText() {
    if (!canSendAnswer || !c.envelope?.currentQuestion) return;
    const text = answerDraft.trim();
    setAnswerDraft("");
    c.submitAnswer(c.envelope.currentQuestion.questionId, null, text);
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
                <BotPulseDot color={flowDone ? BOT.success : BOT.brand} />
                <Text style={{ fontSize: 12, color: BOT.textMuted }}>{flowDone ? "Booking in progress" : "Working on your booking"}</Text>
              </View>
            </View>
          </View>
          <BotStageTracker stages={STAGES} activeIndex={activeStageIndex} allDone={flowDone} />
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
              {c.envelope?.answeredQuestions.map(a => (
                <View key={a.questionId} style={{ gap: 8 }}>
                  <BotAssistantBubble text={a.questionLabel} />
                  <BotUserBubble text={a.answerLabel} />
                </View>
              ))}

              {/* Chronological position matters: the steps for the answer
                  just given belong BELOW that answer and ABOVE the next
                  question, so the trace reads as new work appended to the
                  transcript rather than one line mutating in place. */}
              <BotWorkingTrace entries={trace} />

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
                        c.submitAnswer(c.envelope!.currentQuestion!.questionId, opt.id, null);
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
                {flowDone ? "Fuvay AI is finishing your booking…" : "Choose an option above to continue"}
              </Text>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
