import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Animated, FlatList, KeyboardAvoidingView, Platform, ScrollView,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from "react-native";
import { aiConversationApi, type AISendResponse } from "../lib/api";
import { theme } from "../styles/theme";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Message {
  id:        string;
  role:      "user" | "assistant" | "loading";
  content:   string;
  toolsUsed?: string[];
  timestamp: Date;
  isError?:  boolean;
  fadeAnim?: Animated.Value;
}

// ── Loading message pools ─────────────────────────────────────────────────────
const THINKING_POOL = [
  "Thinking…",
  "Let me check that…",
  "Working on it…",
  "On it…",
  "Give me a second…",
  "Looking into this…",
  "Processing your request…",
  "Almost there…",
  "Figuring that out…",
  "Let me pull that up…",
];

const TOOL_MESSAGE_POOL: Record<string, string[]> = {
  get_my_bookings: [
    "Fetching your bookings…",
    "Looking up your appointments…",
    "Checking your service history…",
    "Pulling up your bookings…",
  ],
  get_booking_detail: [
    "Getting booking details…",
    "Looking up that booking…",
    "Checking the booking status…",
    "Retrieving booking info…",
  ],
  get_active_job: [
    "Tracking your technician…",
    "Checking job progress…",
    "Finding your active service…",
    "Looking up your live job…",
  ],
  get_price_estimate: [
    "Calculating prices…",
    "Getting price estimates…",
    "Checking service rates…",
    "Crunching the numbers…",
  ],
  get_service_faqs: [
    "Finding relevant info…",
    "Looking up service details…",
    "Gathering information…",
    "Checking our knowledge base…",
  ],
};

const AFTER_TOOL_POOL = [
  "Got it, let me put this together…",
  "Found what I need, just a moment…",
  "All set, composing your answer…",
  "Perfect, writing that up…",
  "Done fetching, almost ready…",
];

// ── Quick prompts ─────────────────────────────────────────────────────────────
const QUICK_PROMPTS = [
  { text: "Check my bookings",           icon: "📋" },
  { text: "Track my active job",         icon: "📍" },
  { text: "AC service price in Mumbai",  icon: "💰" },
  { text: "What's included in plumbing?",icon: "🔧" },
  { text: "Book a cleaning service",     icon: "🧹" },
  { text: "Talk to a person",            icon: "🧑‍💼" },
];

// ── Typing dots component ─────────────────────────────────────────────────────
function TypingDots() {
  const dots = [
    useRef(new Animated.Value(0)).current,
    useRef(new Animated.Value(0)).current,
    useRef(new Animated.Value(0)).current,
  ];
  useEffect(() => {
    const anims = dots.map((d, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 160),
          Animated.timing(d, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(d, { toValue: 0, duration: 300, useNativeDriver: true }),
          Animated.delay((2 - i) * 160),
        ])
      )
    );
    anims.forEach(a => a.start());
    return () => anims.forEach(a => a.stop());
  }, []);
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingVertical: 2 }}>
      {dots.map((d, i) => (
        <Animated.View key={i} style={{
          width: 7, height: 7, borderRadius: 3.5,
          backgroundColor: theme.colors.textTertiary,
          opacity: d,
          transform: [{ translateY: d.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }) }],
        }} />
      ))}
    </View>
  );
}

// ── Rotating loading text ─────────────────────────────────────────────────────
function RotatingText({ pool }: { pool: string[] }) {
  const [idx, setIdx] = useState(0);
  const fadeAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const interval = setInterval(() => {
      Animated.sequence([
        Animated.timing(fadeAnim, { toValue: 0, duration: 200, useNativeDriver: true }),
        Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
      ]).start();
      setIdx(i => (i + 1) % pool.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [pool]);

  return (
    <Animated.Text style={[s.loadingText, { opacity: fadeAnim }]}>
      {pool[idx]}
    </Animated.Text>
  );
}

// ── Message fade-in wrapper ───────────────────────────────────────────────────
function FadeInMessage({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(12)).current;
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 250, delay, useNativeDriver: true }),
      Animated.spring(slideAnim, { toValue: 0, tension: 100, friction: 10, delay, useNativeDriver: true }),
    ]).start();
  }, []);
  return (
    <Animated.View style={{ opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}>
      {children}
    </Animated.View>
  );
}

// ── Welcome screen ─────────────────────────────────────────────────────────────
function WelcomeView({ onPrompt }: { onPrompt: (t: string) => void }) {
  return (
    <FadeInMessage>
      <View style={s.welcomeWrap}>
        <View style={s.welcomeLogoWrap}>
          <Text style={s.welcomeLogo}>✦</Text>
        </View>
        <Text style={s.welcomeTitle}>ServiceOS Assistant</Text>
        <Text style={s.welcomeSub}>
          Ask me about your bookings, track your technician,
          get price estimates, or anything about our services.
        </Text>
        <View style={s.promptGrid}>
          {QUICK_PROMPTS.map(p => (
            <TouchableOpacity key={p.text} style={s.promptCard}
              onPress={() => onPrompt(p.text)} activeOpacity={0.75}>
              <Text style={s.promptIcon}>{p.icon}</Text>
              <Text style={s.promptText}>{p.text}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </FadeInMessage>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export function AIChatScreen() {
  const [messages,     setMessages]     = useState<Message[]>([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [loadingPool,  setLoadingPool]  = useState<string[]>(THINKING_POOL);
  const [showWelcome,  setShowWelcome]  = useState(true);
  const [sessionId,    setSessionId]    = useState<string | null>(null);
  const listRef = useRef<FlatList>(null);

  // Ensure a session exists before sending
  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId;
    const session = await aiConversationApi.createSession();
    setSessionId(session.id);
    return session.id;
  }, [sessionId]);

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
    }
  }, [messages]);

  // ── Tool call progress listener ─────────────────────────────────────────────
  // We intercept the API response phases to update the loading message
  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");
    setShowWelcome(false);
    setLoading(true);

    const userMsg: Message = {
      id: `u_${Date.now()}`, role: "user",
      content: msg, timestamp: new Date(),
    };

    const loadingMsg: Message = {
      id: "loading_bubble", role: "loading",
      content: "", timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setLoadingPool(THINKING_POOL);

    // Swap loading pool as we detect tool calls progressing
    // We use a short delay to simulate "seeing" the tool being called
    const poolSwapTimeout = setTimeout(() => {
      setLoadingPool(pickRandom(Object.values(TOOL_MESSAGE_POOL)));
    }, 2500);

    const afterToolTimeout = setTimeout(() => {
      setLoadingPool(AFTER_TOOL_POOL);
    }, 5000);

    try {
      const sid = await ensureSession();
      const res: AISendResponse = await aiConversationApi.sendMessage(sid, msg);

      // Update loading pool based on actual tools used
      if (res.tools_called.length > 0) {
        const lastTool = res.tools_called[res.tools_called.length - 1];
        const toolPool = TOOL_MESSAGE_POOL[lastTool];
        if (toolPool) setLoadingPool(toolPool);
      }

      const aiMsg: Message = {
        id:        `a_${Date.now()}`,
        role:      "assistant",
        content:   res.reply,
        toolsUsed: res.tools_called.length > 0 ? res.tools_called : undefined,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev.filter(m => m.id !== "loading_bubble"), aiMsg]);
    } catch (e: unknown) {
      const errMsg: Message = {
        id:        `err_${Date.now()}`,
        role:      "assistant",
        content:   e instanceof Error ? e.message : "Something went wrong. Please try again.",
        timestamp: new Date(),
        isError:   true,
      };
      setMessages(prev => [...prev.filter(m => m.id !== "loading_bubble"), errMsg]);
    } finally {
      clearTimeout(poolSwapTimeout);
      clearTimeout(afterToolTimeout);
      setLoading(false);
    }
  }

  // ── Render individual message ────────────────────────────────────────────────
  function renderMessage({ item: m, index }: { item: Message; index: number }) {
    const isUser = m.role === "user";

    // Loading bubble
    if (m.role === "loading") {
      return (
        <View style={s.aiBubbleRow}>
          <View style={s.aiIcon}><Text style={s.aiIconText}>✦</Text></View>
          <View style={[s.aiBubble, s.loadingBubble]}>
            <TypingDots />
            <RotatingText pool={loadingPool} />
          </View>
        </View>
      );
    }

    return (
      <FadeInMessage delay={30}>
        {isUser ? (
          // User message
          <View style={s.userBubbleRow}>
            <View style={s.userBubble}>
              <Text style={s.userText}>{m.content}</Text>
            </View>
          </View>
        ) : (
          // AI message
          <View style={s.aiBubbleRow}>
            <View style={s.aiIcon}>
              <Text style={s.aiIconText}>✦</Text>
            </View>
            <View style={{ flex: 1 }}>
              <View style={[s.aiBubble, m.isError && s.errorBubble]}>
                <Text style={[s.aiText, m.isError && { color: theme.colors.dangerText }]}>
                  {m.content}
                </Text>
              </View>

              {/* Tool pill row */}
              {m.toolsUsed && m.toolsUsed.length > 0 && (
                <View style={s.toolPillRow}>
                  {m.toolsUsed.map((tool, i) => (
                    <View key={i} style={s.toolPill}>
                      <Text style={s.toolPillDot}>◉</Text>
                      <Text style={s.toolPillText}>
                        {TOOL_PILL_LABELS[tool] ?? tool.replace(/_/g, " ")}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Timestamp */}
              <Text style={s.timestamp}>
                {m.timestamp.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
              </Text>
            </View>
          </View>
        )}
      </FadeInMessage>
    );
  }

  return (
    <KeyboardAvoidingView
      style={s.screen}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={90}>

      {/* Top bar */}
      <View style={s.topBar}>
        <View style={s.topBarLeft}>
          <View style={s.topBarIcon}><Text style={s.topBarIconText}>✦</Text></View>
          <View>
            <Text style={s.topBarTitle}>ServiceOS AI</Text>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
              <View style={[s.statusDot, loading && { backgroundColor: theme.colors.warning }]} />
              <Text style={s.topBarSub}>{loading ? "Working…" : "Ready"}</Text>
            </View>
          </View>
        </View>
        {messages.length > 0 && (
          <TouchableOpacity style={s.clearBtn}
            onPress={() => { setMessages([]); setShowWelcome(true); setLoading(false); }}
            activeOpacity={0.7}>
            <Text style={s.clearBtnText}>New chat</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Message list or welcome */}
      {showWelcome && messages.length === 0 ? (
        <ScrollView
          contentContainerStyle={s.welcomeScroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <WelcomeView onPrompt={t => send(t)} />
        </ScrollView>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={m => m.id}
          renderItem={renderMessage}
          contentContainerStyle={s.messageList}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          showsVerticalScrollIndicator={false}
        />
      )}

      {/* Input bar */}
      <View style={s.inputWrap}>
        {/* Quick prompts strip — shown while input is focused and messages exist */}
        <TextInput
          style={s.input}
          value={input}
          onChangeText={setInput}
          placeholder="Message ServiceOS AI…"
          placeholderTextColor={theme.colors.textTertiary}
          multiline
          maxLength={2000}
          editable={!loading}
          returnKeyType="default"
        />
        <TouchableOpacity
          style={[s.sendBtn, (!input.trim() || loading) && s.sendBtnDisabled]}
          onPress={() => send()}
          disabled={!input.trim() || loading}
          activeOpacity={0.8}>
          {loading ? (
            <View style={s.stopDot} />
          ) : (
            <Text style={s.sendArrow}>↑</Text>
          )}
        </TouchableOpacity>
      </View>
      <Text style={s.disclaimer}>AI responses may be incorrect. Verify important info.</Text>
    </KeyboardAvoidingView>
  );
}

// ── Tool pill labels ───────────────────────────────────────────────────────────
const TOOL_PILL_LABELS: Record<string, string> = {
  get_my_bookings:    "Checked bookings",
  get_booking_detail: "Retrieved booking",
  get_active_job:     "Tracked live job",
  get_price_estimate: "Got price estimate",
  get_service_faqs:   "Looked up FAQs",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  screen:            { flex: 1, backgroundColor: "#F7F7F8" },

  // Top bar
  topBar:            { flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                       paddingHorizontal: 16, paddingVertical: 12,
                       backgroundColor: theme.colors.surface,
                       borderBottomWidth: 1, borderBottomColor: theme.colors.border },
  topBarLeft:        { flexDirection: "row", alignItems: "center", gap: 10 },
  topBarIcon:        { width: 34, height: 34, borderRadius: 10,
                       backgroundColor: theme.colors.brand,
                       alignItems: "center", justifyContent: "center" },
  topBarIconText:    { color: "#fff", fontSize: 16, fontWeight: "700" },
  topBarTitle:       { fontSize: 15, fontWeight: "700", color: theme.colors.textPrimary },
  topBarSub:         { fontSize: 11, color: theme.colors.textTertiary },
  statusDot:         { width: 6, height: 6, borderRadius: 3, backgroundColor: theme.colors.success },
  clearBtn:          { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8,
                       backgroundColor: theme.colors.surfaceSunken,
                       borderWidth: 1, borderColor: theme.colors.border },
  clearBtnText:      { fontSize: 12, color: theme.colors.textSecondary, fontWeight: "600" },

  // Welcome
  welcomeScroll:     { flexGrow: 1, justifyContent: "center", padding: 20 },
  welcomeWrap:       { alignItems: "center", paddingVertical: 20, gap: 14 },
  welcomeLogoWrap:   { width: 56, height: 56, borderRadius: 16,
                       backgroundColor: theme.colors.brand,
                       alignItems: "center", justifyContent: "center",
                       marginBottom: 6, ...theme.shadow.md },
  welcomeLogo:       { fontSize: 26, color: "#fff" },
  welcomeTitle:      { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary,
                       letterSpacing: -0.5, textAlign: "center" },
  welcomeSub:        { fontSize: 14, color: theme.colors.textSecondary, textAlign: "center",
                       lineHeight: 21, maxWidth: 300 },
  promptGrid:        { width: "100%", gap: 8, marginTop: 8 },
  promptCard:        { flexDirection: "row", alignItems: "center", gap: 12,
                       backgroundColor: theme.colors.surface,
                       borderRadius: 12, padding: 14,
                       borderWidth: 1, borderColor: theme.colors.border,
                       ...theme.shadow.sm },
  promptIcon:        { fontSize: 20, width: 28 },
  promptText:        { fontSize: 14, color: theme.colors.textPrimary, fontWeight: "500", flex: 1 },

  // Messages
  messageList:       { padding: 16, gap: 16, paddingBottom: 8 },

  // AI bubble
  aiBubbleRow:       { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  aiIcon:            { width: 28, height: 28, borderRadius: 8,
                       backgroundColor: theme.colors.brand,
                       alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 },
  aiIconText:        { color: "#fff", fontSize: 13, fontWeight: "700" },
  aiBubble:          { flex: 1, backgroundColor: theme.colors.surface,
                       borderRadius: 16, borderTopLeftRadius: 4,
                       paddingHorizontal: 14, paddingVertical: 12,
                       borderWidth: 1, borderColor: theme.colors.border,
                       ...theme.shadow.sm },
  loadingBubble:     { flexDirection: "row", alignItems: "center", gap: 10,
                       paddingVertical: 10, flex: 0, alignSelf: "flex-start" },
  aiText:            { fontSize: 15, color: theme.colors.textPrimary, lineHeight: 23 },
  errorBubble:       { backgroundColor: theme.colors.dangerBg, borderColor: theme.colors.dangerBorder },
  loadingText:       { fontSize: 13, color: theme.colors.textTertiary, fontStyle: "italic" },

  // User bubble
  userBubbleRow:     { alignItems: "flex-end" },
  userBubble:        { backgroundColor: theme.colors.brand, borderRadius: 16,
                       borderBottomRightRadius: 4,
                       paddingHorizontal: 14, paddingVertical: 12, maxWidth: "82%" },
  userText:          { fontSize: 15, color: "#fff", lineHeight: 23 },

  // Tool pills
  toolPillRow:       { flexDirection: "row", flexWrap: "wrap", gap: 5, marginTop: 8 },
  toolPill:          { flexDirection: "row", alignItems: "center", gap: 4,
                       backgroundColor: theme.colors.accentLight,
                       borderRadius: 20, paddingHorizontal: 8, paddingVertical: 3,
                       borderWidth: 1, borderColor: theme.colors.infoBorder },
  toolPillDot:       { fontSize: 8, color: theme.colors.accent },
  toolPillText:      { fontSize: 10, color: theme.colors.accent, fontWeight: "600" },

  // Timestamp
  timestamp:         { fontSize: 10, color: theme.colors.textTertiary, marginTop: 5, marginLeft: 2 },

  // Input bar
  inputWrap:         { flexDirection: "row", alignItems: "flex-end", gap: 8,
                       paddingHorizontal: 12, paddingTop: 10, paddingBottom: 6,
                       backgroundColor: theme.colors.surface,
                       borderTopWidth: 1, borderTopColor: theme.colors.border },
  input:             { flex: 1, minHeight: 42, maxHeight: 120,
                       borderWidth: 1.5, borderColor: theme.colors.border,
                       borderRadius: 22, paddingHorizontal: 16, paddingVertical: 10,
                       fontSize: 15, color: theme.colors.textPrimary,
                       backgroundColor: "#F7F7F8", lineHeight: 21 },
  sendBtn:           { width: 42, height: 42, borderRadius: 21,
                       backgroundColor: theme.colors.brand,
                       alignItems: "center", justifyContent: "center",
                       ...theme.shadow.sm },
  sendBtnDisabled:   { backgroundColor: theme.colors.border },
  sendArrow:         { color: "#fff", fontSize: 20, fontWeight: "700", marginTop: -1 },
  stopDot:           { width: 12, height: 12, borderRadius: 3, backgroundColor: "#fff" },

  // Disclaimer
  disclaimer:        { fontSize: 10, color: theme.colors.textTertiary,
                       textAlign: "center", paddingVertical: 5,
                       backgroundColor: theme.colors.surface },
});
