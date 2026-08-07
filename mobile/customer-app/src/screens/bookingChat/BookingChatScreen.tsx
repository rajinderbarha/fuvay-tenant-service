import React, { useEffect, useMemo, useState } from "react";
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
import { BOT } from "../../components/bookingChat/botTheme";
import {
  BotStageTracker, BotAssistantBubble, BotUserBubble, BotOptionChips, BotWorkingStep, BotTypingDots,
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
          <Text style={{ color: BOT.textMuted, fontSize: 12.5 }}>Loading your assistant</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!entryContext.zipcode) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 12, paddingHorizontal: 32 }}>
          <Ionicons name="location-outline" size={32} color={BOT.textFaint} />
          <Text style={{ color: BOT.textPrimary, fontSize: 15, fontWeight: "700", textAlign: "center" }}>Choose your location first</Text>
          <Text style={{ color: BOT.textMuted, fontSize: 12.5, textAlign: "center" }}>
            Fuvay Assistant needs your service location to check what's available.
          </Text>
          <Pressable
            onPress={() => navigation.navigate("Home" as never)}
            accessibilityRole="button"
            accessibilityLabel="Go to Home"
            style={{ marginTop: 8, height: 40, paddingHorizontal: 20, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}
          >
            <Text style={{ color: BOT.bg, fontSize: 13, fontWeight: "700" }}>Go to Home</Text>
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
  const navigation = useNavigation();
  const c = useAssistantController(entryContext, customerId);
  const zipcode = entryContext.zipcode;

  const [selectedIssueLabel, setSelectedIssueLabel] = useState<string | null>(null);
  const [answerDraft, setAnswerDraft] = useState("");

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

  const activeStageIndex = !c.draftId ? 0 : !questionsComplete ? 0 : !addr.resolvedAddressId ? 1 : 2;

  function submitFreeText() {
    const text = answerDraft.trim();
    if (!text || !c.envelope?.currentQuestion) return;
    setAnswerDraft("");
    c.submitAnswer(c.envelope.currentQuestion.questionId, null, text);
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BOT.bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {/* Header */}
        <View style={{ paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: BOT.borderSubtle }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close" style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border }}>
              <Ionicons name="chevron-back" size={17} color={BOT.textTertiary} />
            </Pressable>
            <View style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}>
              <Ionicons name="sparkles" size={16} color={BOT.bg} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ fontSize: 14.5, fontWeight: "700", color: BOT.textPrimary }}>Fuvay AI</Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: flowDone ? BOT.success : BOT.brand }} />
                <Text style={{ fontSize: 11, color: BOT.textMuted }}>{flowDone ? "Booking in progress" : "Working on your booking"}</Text>
              </View>
            </View>
          </View>
          <BotStageTracker stages={STAGES} activeIndex={activeStageIndex} allDone={flowDone} />
        </View>

        {/* Transcript */}
        <FlatList
          style={{ flex: 1 }}
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
              {c.activityStage && (c.uiState === "assistant_processing" || c.uiState === "submitting_answer") ? (
                <BotWorkingStep label={resolveActivityLabel(c.activityStage, zipcode)} status="pending" />
              ) : null}

              {c.offeringChoice && !selectedIssueLabel ? (
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
              {c.envelope?.currentQuestion && !questionsComplete ? (
                <View style={{ gap: 8 }}>
                  <BotAssistantBubble text={c.envelope.currentQuestion.text} />
                  {c.envelope.currentQuestion.acceptsFreeText ? (
                    <View style={{ marginLeft: 36, flexDirection: "row", gap: 8, alignItems: "center" }}>
                      <TextInput
                        value={answerDraft}
                        onChangeText={setAnswerDraft}
                        onSubmitEditing={submitFreeText}
                        placeholder="Type your answer"
                        placeholderTextColor={BOT.textFaint}
                        style={{ flex: 1, height: 40, borderRadius: 20, paddingHorizontal: 14, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border, color: BOT.textPrimary, fontSize: 12.5 }}
                      />
                      <Pressable onPress={submitFreeText} style={{ width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand }}>
                        <Ionicons name="send" size={15} color={BOT.bg} />
                      </Pressable>
                    </View>
                  ) : (
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
              {addressPhaseActive && !addr.resolvedAddressId ? (
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

        {/* Composer -- decorative once every real turn has its own input;
            kept for parity with the reference's always-visible bar. */}
        <View style={{ paddingHorizontal: 16, paddingVertical: 14, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, backgroundColor: BOT.bgComposer }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, borderRadius: 24, paddingHorizontal: 16, height: 48, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.border }}>
            <Text style={{ flex: 1, fontSize: 13, color: BOT.textDim }} numberOfLines={1}>
              Fuvay AI is handling this for you…
            </Text>
            <Ionicons name="mic-outline" size={17} color={BOT.textDim} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
