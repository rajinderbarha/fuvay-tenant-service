import React, { useCallback, useEffect, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { chatApi, type ChatMessage } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Skeleton } from "../components/Skeleton";
import { theme } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { roomId:string; name:string };
type Props  = NativeStackScreenProps<{ ChatRoom:Params }, "ChatRoom">;

export function ChatRoomScreen({ route }: Props) {
  const { roomId, name } = route.params;
  const { user } = useAuth();
  const [text, setText] = useState("");
  const listRef = useRef<FlatList>(null);

  const messages = useApi(useCallback(() => chatApi.getMessages(roomId), [roomId]));
  const sendAction = useAction(useCallback(
    (content:string) => chatApi.sendMessage(roomId, content), [roomId]
  ));

  useEffect(() => {
    chatApi.markRead(roomId).catch(() => {});
  }, [roomId]);

  useEffect(() => {
    if (messages.data?.messages.length) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated:false }), 100);
    }
  }, [messages.data]);

  async function handleSend() {
    const trimmed = text.trim(); if (!trimmed) return;
    setText("");
    const res = await sendAction.execute(trimmed);
    if (res) messages.refetch();
  }

  const fmtTime = (d:string) => new Date(d).toLocaleTimeString("en-IN",{ hour:"2-digit", minute:"2-digit" });

  function renderMessage({ item:m }: { item:ChatMessage }) {
    const isMe = m.sender_id === user?.id;
    return (
      <View style={[s.msgRow, isMe ? s.msgRight : s.msgLeft]}>
        <View style={[s.bubble, isMe ? s.bubbleMe : s.bubbleOther]}>
          <Text style={[s.msgText, isMe && { color:"#fff" }]}>{m.content}</Text>
        </View>
        <Text style={s.msgTime}>{fmtTime(m.sent_at)}</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex:1, backgroundColor:theme.colors.bg }}
      behavior={Platform.OS==="ios"?"padding":"height"} keyboardVerticalOffset={90}>
      {messages.loading ? (
        <View style={{ padding:16, gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={44} />)}
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={messages.data?.messages ?? []}
          renderItem={renderMessage}
          keyExtractor={m => m.message_id}
          contentContainerStyle={{ padding:14, gap:10 }}
        />
      )}

      {/* Input bar */}
      <View style={s.inputBar}>
        <TextInput
          style={s.input} value={text} onChangeText={setText}
          placeholder="Type a message…" placeholderTextColor={theme.colors.textTertiary}
          multiline maxLength={1000} returnKeyType="send"
          onSubmitEditing={Platform.OS==="ios" ? handleSend : undefined}
        />
        <TouchableOpacity style={[s.sendBtn, !text.trim() && { opacity:0.4 }]}
          onPress={handleSend} disabled={!text.trim() || sendAction.loading}>
          <Text style={s.sendText}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  msgRow:     { maxWidth:"78%", gap:4 },
  msgLeft:    { alignSelf:"flex-start" },
  msgRight:   { alignSelf:"flex-end", alignItems:"flex-end" },
  bubble:     { borderRadius:16, paddingHorizontal:13, paddingVertical:9 },
  bubbleMe:   { backgroundColor:theme.colors.brand, borderBottomRightRadius:4 },
  bubbleOther:{ backgroundColor:theme.colors.surface, borderBottomLeftRadius:4, ...theme.shadow.sm },
  msgText:    { fontSize:theme.font.size.base, color:theme.colors.textPrimary, lineHeight:20 },
  msgTime:    { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  inputBar:   { flexDirection:"row", alignItems:"flex-end", gap:10, padding:12,
                backgroundColor:theme.colors.surface, borderTopWidth:1, borderTopColor:theme.colors.border },
  input:      { flex:1, minHeight:40, maxHeight:100, borderWidth:1, borderColor:theme.colors.border,
                borderRadius:20, paddingHorizontal:14, paddingVertical:9, fontSize:theme.font.size.base,
                color:theme.colors.textPrimary, backgroundColor:theme.colors.surfaceSunken },
  sendBtn:    { width:40, height:40, borderRadius:20, backgroundColor:theme.colors.brand,
                alignItems:"center", justifyContent:"center" },
  sendText:   { color:"#fff", fontSize:20, fontWeight:"700" },
});
