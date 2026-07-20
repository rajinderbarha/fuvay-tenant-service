import React, { useCallback, useState } from "react";
import {
  FlatList, KeyboardAvoidingView, Modal, Platform, StyleSheet, Text,
  TextInput, TouchableOpacity, View,
} from "react-native";
import { aiConversationApi, type AISession } from "../lib/api";
import { CHAT_LANGUAGES, searchChatLanguages, type ChatLanguageOption } from "../lib/chatLanguages";
import { theme } from "../styles/theme";

/**
 * UX-06 Round 2 — real DeepSeek conversational booking chat entry, built against
 * the CONFIRMED live contract (not a guess):
 *   POST /v1/customer/ai-chat/sessions              -> creates a real session row
 *   POST /v1/customer/ai-chat/sessions/{id}/messages -> real DeepSeek tool-call
 *     loop, response shape { reply, tools_called, intent, session }
 * Confirmed via source read of app/engines/ai_conversation/{customer_router,
 * service}.py AND live curl probes against the running backend this round (see
 * docs/design/ux-06-customer-app/deepseek-conversation-contract.md for the full
 * evidence trail, including the graceful-fallback reply this dev environment's
 * placeholder DEEPSEEK_API_KEY produces — an infra limitation, not a UI bug).
 *
 * The language selector below is scoped to THIS SCREEN ONLY, per the hard
 * language-architecture rule — it must never be reused for app-wide navigation
 * or ordinary screens. The backend has no language field, so the selection is
 * folded into each outgoing message via withLanguageInstruction (see lib/api.ts)
 * and kept purely as local UI/conversation state.
 *
 * NOT YET wired into AppNavigator/TabNavigator this round — four overlapping
 * legacy chat-shaped screens already exist (AIChatScreen, AIAssistantScreen,
 * SmartBotScreen, ChatScreen) and consolidating navigation onto this one is
 * deferred to the next round (see deferred-items.md) rather than risk breaking
 * existing routes under this round's time constraints.
 */
type Msg = { id:string; role:"user"|"assistant"; content:string };

export function DeepSeekChatScreen() {
  const [session, setSession]   = useState<AISession | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput]       = useState("");
  const [sending, setSending]   = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError]       = useState<string|null>(null);
  const [language, setLanguage] = useState<ChatLanguageOption>(CHAT_LANGUAGES[0]);
  const [langModal, setLangModal] = useState(false);
  const [langQuery, setLangQuery] = useState("");

  const startSession = useCallback(async () => {
    setStarting(true); setError(null);
    try {
      const s = await aiConversationApi.createSession();
      setSession(s);
      setMessages([]);
    } catch (e:unknown) {
      setError(e instanceof Error ? e.message : "Could not start a conversation. Please try again.");
    } finally { setStarting(false); }
  }, []);

  async function send() {
    const text = input.trim();
    if (!text || !session || sending) return;
    setInput("");
    setMessages(m => [...m, { id:`u${m.length}`, role:"user", content:text }]);
    setSending(true); setError(null);
    try {
      const res = await aiConversationApi.sendMessage(session.id, text, language);
      setMessages(m => [...m, { id:`a${m.length}`, role:"assistant", content:res.reply }]);
      setSession(res.session);
    } catch (e:unknown) {
      setError(e instanceof Error ? e.message : "Message failed to send. Please try again.");
    } finally { setSending(false); }
  }

  if (!session) {
    return (
      <View style={[s.screen, s.center]}>
        <Text style={s.icon}>🤖</Text>
        <Text style={s.title}>Talk to ServiceOS Assistant</Text>
        <Text style={s.body}>Describe what you need in your own words — the assistant can look up services, pricing, and help you book.</Text>
        {error && <Text style={s.errorText}>{error}</Text>}
        <TouchableOpacity style={s.startBtn} onPress={startSession} disabled={starting} testID="chat-start">
          <Text style={s.startBtnText}>{starting ? "Starting…" : "Start Conversation"}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      <View style={s.header}>
        <TouchableOpacity style={s.langChip} onPress={()=>setLangModal(true)} testID="chat-language-btn">
          <Text style={s.langChipText}>{language.nativeName} ▾</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={messages}
        keyExtractor={m=>m.id}
        contentContainerStyle={s.list}
        renderItem={({item}) => (
          <View style={[s.bubble, item.role==="user" ? s.bubbleUser : s.bubbleAssistant]}>
            <Text style={item.role==="user" ? s.bubbleUserText : s.bubbleAssistantText}>{item.content}</Text>
          </View>
        )}
      />

      {error && <Text style={s.errorText}>{error}</Text>}

      <View style={s.inputRow}>
        <TextInput
          style={s.input} value={input} onChangeText={setInput}
          placeholder="Type a message…" placeholderTextColor={theme.colors.textTertiary}
          testID="chat-input"
        />
        <TouchableOpacity style={s.sendBtn} onPress={send} disabled={sending} testID="chat-send">
          <Text style={s.sendBtnText}>{sending ? "…" : "Send"}</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={langModal} animationType="slide" onRequestClose={()=>setLangModal(false)}>
        <View style={s.langModal}>
          <TextInput
            style={s.langSearch} value={langQuery} onChangeText={setLangQuery}
            placeholder="Search language…" placeholderTextColor={theme.colors.textTertiary}
            testID="chat-language-search"
          />
          <FlatList
            data={searchChatLanguages(langQuery)}
            keyExtractor={l=>l.code}
            renderItem={({item}) => (
              <TouchableOpacity style={s.langRow} onPress={()=>{ setLanguage(item); setLangModal(false); setLangQuery(""); }}>
                <Text style={s.langRowNative}>{item.nativeName}</Text>
                <Text style={s.langRowEnglish}>{item.englishName} ({item.code})</Text>
              </TouchableOpacity>
            )}
          />
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  screen: { flex:1, backgroundColor:theme.colors.bg },
  center: { alignItems:"center", justifyContent:"center", padding:32, gap:14 },
  icon:   { fontSize:48 },
  title:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
  body:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center", lineHeight:20 },
  errorText: { color:theme.colors.dangerText, fontSize:theme.font.size.sm, textAlign:"center", paddingHorizontal:16 },
  startBtn: { backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg, paddingVertical:14, paddingHorizontal:28 },
  startBtnText: { color:"#fff", fontWeight:"700", fontSize:theme.font.size.base },
  header: { flexDirection:"row", justifyContent:"flex-end", padding:10, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  langChip: { paddingHorizontal:12, paddingVertical:6, borderRadius:theme.radius.full, backgroundColor:theme.colors.surfaceSunken },
  langChipText: { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
  list: { padding:14, gap:10 },
  bubble: { maxWidth:"80%", borderRadius:theme.radius.lg, padding:12 },
  bubbleUser: { alignSelf:"flex-end", backgroundColor:theme.colors.brand },
  bubbleAssistant: { alignSelf:"flex-start", backgroundColor:theme.colors.surfaceSunken },
  bubbleUserText: { color:"#fff", fontSize:theme.font.size.base },
  bubbleAssistantText: { color:theme.colors.textPrimary, fontSize:theme.font.size.base },
  inputRow: { flexDirection:"row", gap:8, padding:12, borderTopWidth:1, borderTopColor:theme.colors.border },
  input: { flex:1, height:44, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
           paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
           backgroundColor:theme.colors.surfaceSunken },
  sendBtn: { justifyContent:"center", paddingHorizontal:18, borderRadius:theme.radius.lg, backgroundColor:theme.colors.brand },
  sendBtnText: { color:"#fff", fontWeight:"700" },
  langModal: { flex:1, backgroundColor:theme.colors.bg, paddingTop:60, paddingHorizontal:16 },
  langSearch: { height:44, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                backgroundColor:theme.colors.surfaceSunken, marginBottom:12 },
  langRow: { paddingVertical:12, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  langRowNative: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  langRowEnglish: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
});
