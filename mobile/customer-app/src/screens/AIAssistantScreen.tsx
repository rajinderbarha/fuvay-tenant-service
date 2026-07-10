import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  ActivityIndicator, FlatList, KeyboardAvoidingView,
  Platform, StyleSheet, Text, TextInput,
  TouchableOpacity, View, Alert,
} from "react-native";
import { useAction } from "../hooks/useApi";
import { aiApi }     from "../lib/api";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Message {
  id:           string;
  role:         "user" | "assistant";
  content:      string;
  booking?:     BookingSuggestion | null;
  timestamp:    Date;
}

interface BookingSuggestion {
  category_id:  string;
  service_name: string;
  job_type:     "repair" | "maintenance" | "consultation";
  visit_fee?:   number;
  fixed_price?: number;
  consult_fee?: number;
}

// Parse <BOOK>{...}</BOOK> from AI response
function parseBookingSuggestion(text: string): { clean: string; booking: BookingSuggestion | null } {
  const match = text.match(/<BOOK>([\s\S]*?)<\/BOOK>/);
  if (!match) return { clean: text, booking: null };
  try {
    const booking = JSON.parse(match[1].trim()) as BookingSuggestion;
    const clean   = text.replace(/<BOOK>[\s\S]*?<\/BOOK>/, "").trim();
    return { clean, booking };
  } catch {
    return { clean: text.replace(/<BOOK>[\s\S]*?<\/BOOK>/, "").trim(), booking: null };
  }
}

// ── Suggested starters ────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "My AC is not cooling",
  "I want to get my AC serviced",
  "There's a pipe leaking in my bathroom",
  "Cockroaches in my kitchen",
  "I don't know what's wrong with my washing machine",
  "I want to repaint my bedroom",
];

// ── Main component ────────────────────────────────────────────────────────────
type Props = NativeStackScreenProps<{ AIAssistant: undefined }, "AIAssistant">;

export function AIAssistantScreen({ navigation }: Props) {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [history,   setHistory]   = useState<{ role: string; content: string }[]>([]);
  const listRef = useRef<FlatList>(null);

  const chatAction = useAction(
    useCallback((msg: string, hist: typeof history) =>
      aiApi.chat(msg, hist), [])
  );

  // ── Greeting on mount ──────────────────────────────────────────────────────
  useEffect(() => {
    setMessages([{
      id:        "welcome",
      role:      "assistant",
      content:   "Hi! 👋 I'm your ServiceOS assistant.\n\nTell me what's going on at home and I'll figure out exactly what kind of service you need — repair, routine maintenance, or a consultation.",
      booking:   null,
      timestamp: new Date(),
    }]);
  }, []);

  // ── Scroll to bottom ───────────────────────────────────────────────────────
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages]);

  // ── Send message ───────────────────────────────────────────────────────────
  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg) return;
    setInput("");

    const userMsg: Message = {
      id: `u-${Date.now()}`, role: "user",
      content: msg, booking: null, timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);

    const newHistory = [...history, { role: "user", content: msg }];
    const res = await chatAction.execute(msg, history);

    if (res?.reply) {
      const { clean, booking } = parseBookingSuggestion(res.reply);
      const assistantMsg: Message = {
        id: `a-${Date.now()}`, role: "assistant",
        content: clean, booking, timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      setHistory([...newHistory, { role: "assistant", content: res.reply }]);
    } else if (chatAction.error) {
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`, role: "assistant",
        content: "Sorry, I ran into an issue. Please try again.",
        booking: null, timestamp: new Date(),
      }]);
    }
  }

  // ── Book from AI suggestion ────────────────────────────────────────────────
  function handleBook(booking: BookingSuggestion) {
    navigation.navigate("BookService" as never, {
      categoryId: booking.category_id,
      preselectedService: booking.service_name,
      jobType: booking.job_type,
    } as never);
  }

  // ── Price label helper ─────────────────────────────────────────────────────
  function priceLabel(b: BookingSuggestion): string {
    if (b.job_type === "repair")        return `₹${b.visit_fee} visit fee`;
    if (b.job_type === "maintenance")   return `₹${b.fixed_price?.toLocaleString("en-IN")} fixed`;
    if (b.job_type === "consultation")  return `₹${b.consult_fee} consult fee`;
    return "";
  }

  const typeColors = {
    repair:       { color: "#DC2626", bg: "#FEF2F2", border: "#FECACA", icon: "🔧" },
    maintenance:  { color: "#16A34A", bg: "#F0FDF4", border: "#BBF7D0", icon: "⚙️" },
    consultation: { color: "#7C3AED", bg: "#F5F3FF", border: "#DDD6FE", icon: "📋" },
  };

  // ── Render message ─────────────────────────────────────────────────────────
  function renderMessage({ item }: { item: Message }) {
    const isUser = item.role === "user";
    return (
      <View style={[s.msgWrap, isUser ? s.msgWrapUser : s.msgWrapAI]}>
        {!isUser && (
          <View style={s.avatar}>
            <Text style={{ fontSize: 16 }}>🤖</Text>
          </View>
        )}
        <View style={{ maxWidth: "80%", gap: 8 }}>
          <View style={[s.bubble, isUser ? s.bubbleUser : s.bubbleAI]}>
            <Text style={[s.bubbleText, isUser ? s.bubbleTextUser : s.bubbleTextAI]}>
              {item.content}
            </Text>
          </View>

          {/* Booking suggestion card */}
          {item.booking && (() => {
            const tc = typeColors[item.booking.job_type] ?? typeColors.repair;
            return (
              <View style={[s.bookCard, { borderColor: tc.border, backgroundColor: tc.bg }]}>
                <View style={[gs.row, { gap: 8, marginBottom: 8 }]}>
                  <Text style={{ fontSize: 20 }}>{tc.icon}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={[s.bookServiceName, { color: tc.color }]}>
                      {item.booking.service_name}
                    </Text>
                    <Text style={s.bookPrice}>{priceLabel(item.booking)}</Text>
                  </View>
                </View>
                {item.booking.job_type === "repair" && (
                  <Text style={s.bookNote}>
                    ⚠ Final repair cost quoted after inspection. You approve before any work starts.
                  </Text>
                )}
                <TouchableOpacity
                  style={[s.bookBtn, { backgroundColor: tc.color }]}
                  onPress={() => handleBook(item.booking!)}
                  activeOpacity={0.85}>
                  <Text style={s.bookBtnText}>Book Now →</Text>
                </TouchableOpacity>
              </View>
            );
          })()}
        </View>
      </View>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <KeyboardAvoidingView
      style={gs.screen}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={90}>

      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={m => m.id}
        renderItem={renderMessage}
        contentContainerStyle={s.list}
        ListFooterComponent={
          chatAction.loading
            ? <View style={s.typingWrap}>
                <View style={s.avatar}><Text style={{ fontSize: 16 }}>🤖</Text></View>
                <View style={s.typingBubble}>
                  <Text style={s.typingDots}>● ● ●</Text>
                </View>
              </View>
            : null
        }
      />

      {/* Suggestions — only on first message */}
      {messages.length === 1 && (
        <View style={s.suggestionsWrap}>
          <FlatList
            horizontal showsHorizontalScrollIndicator={false}
            data={SUGGESTIONS}
            keyExtractor={s => s}
            contentContainerStyle={{ paddingHorizontal: 12, gap: 8 }}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={s.suggestion}
                onPress={() => handleSend(item)}
                activeOpacity={0.8}>
                <Text style={s.suggestionText}>{item}</Text>
              </TouchableOpacity>
            )}
          />
        </View>
      )}

      {/* Input bar */}
      <View style={s.inputBar}>
        <TextInput
          style={s.input}
          value={input}
          onChangeText={setInput}
          placeholder="Describe your problem…"
          placeholderTextColor={theme.colors.textTertiary}
          multiline
          maxLength={500}
          onSubmitEditing={() => handleSend()}
          returnKeyType="send"
        />
        <TouchableOpacity
          style={[s.sendBtn, (!input.trim() || chatAction.loading) && s.sendBtnDisabled]}
          onPress={() => handleSend()}
          disabled={!input.trim() || chatAction.loading}
          activeOpacity={0.85}>
          {chatAction.loading
            ? <ActivityIndicator size="small" color="white" />
            : <Text style={s.sendIcon}>↑</Text>
          }
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  list:          { padding: 12, paddingBottom: 8, gap: 12 },
  // Messages
  msgWrap:       { flexDirection: "row", gap: 8, alignItems: "flex-end" },
  msgWrapUser:   { flexDirection: "row-reverse" },
  msgWrapAI:     { flexDirection: "row" },
  avatar:        { width: 32, height: 32, borderRadius: 16,
                   backgroundColor: theme.colors.accent + "20",
                   alignItems: "center", justifyContent: "center", flexShrink: 0 },
  bubble:        { borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10, maxWidth: "100%" },
  bubbleUser:    { backgroundColor: theme.colors.brand, borderBottomRightRadius: 4 },
  bubbleAI:      { backgroundColor: theme.colors.surface, borderBottomLeftRadius: 4,
                   borderWidth: 1, borderColor: theme.colors.border },
  bubbleText:    { fontSize: theme.font.size.base, lineHeight: 22 },
  bubbleTextUser:{ color: "#fff" },
  bubbleTextAI:  { color: theme.colors.textPrimary },
  // Booking card
  bookCard:      { borderRadius: theme.radius.lg, borderWidth: 1.5, padding: 14, gap: 6 },
  bookServiceName:{ fontSize: theme.font.size.base, fontWeight: "800" },
  bookPrice:     { fontSize: theme.font.size.sm, color: theme.colors.textSecondary, marginTop: 2 },
  bookNote:      { fontSize: theme.font.size.xs, color: theme.colors.textSecondary,
                   lineHeight: 18, paddingTop: 4,
                   borderTopWidth: 1, borderTopColor: theme.colors.border },
  bookBtn:       { borderRadius: theme.radius.md, paddingVertical: 10,
                   alignItems: "center", marginTop: 4 },
  bookBtnText:   { color: "#fff", fontWeight: "700", fontSize: theme.font.size.base },
  // Typing indicator
  typingWrap:    { flexDirection: "row", gap: 8, alignItems: "flex-end", paddingHorizontal: 12, paddingBottom: 8 },
  typingBubble:  { backgroundColor: theme.colors.surface, borderRadius: 18,
                   borderBottomLeftRadius: 4, paddingHorizontal: 14, paddingVertical: 12,
                   borderWidth: 1, borderColor: theme.colors.border },
  typingDots:    { fontSize: 10, color: theme.colors.textTertiary, letterSpacing: 4 },
  // Suggestions
  suggestionsWrap:{ paddingVertical: 10, borderTopWidth: 1, borderTopColor: theme.colors.border },
  suggestion:    { paddingHorizontal: 14, paddingVertical: 8, borderRadius: theme.radius.full,
                   backgroundColor: theme.colors.surface, borderWidth: 1,
                   borderColor: theme.colors.border },
  suggestionText:{ fontSize: theme.font.size.sm, color: theme.colors.textSecondary, fontWeight: "500" },
  // Input bar
  inputBar:      { flexDirection: "row", gap: 8, padding: 12, alignItems: "flex-end",
                   borderTopWidth: 1, borderTopColor: theme.colors.border,
                   backgroundColor: theme.colors.surface },
  input:         { flex: 1, minHeight: 44, maxHeight: 120, borderRadius: theme.radius.lg,
                   borderWidth: 1.5, borderColor: theme.colors.border,
                   paddingHorizontal: 14, paddingVertical: 10,
                   fontSize: theme.font.size.base, color: theme.colors.textPrimary,
                   backgroundColor: theme.colors.surfaceSunken },
  sendBtn:       { width: 44, height: 44, borderRadius: 22, backgroundColor: theme.colors.brand,
                   alignItems: "center", justifyContent: "center" },
  sendBtnDisabled:{ opacity: 0.4 },
  sendIcon:      { fontSize: 20, color: "#fff", fontWeight: "700" },
});
