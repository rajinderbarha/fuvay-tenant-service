import React, { useCallback, useEffect, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { chatApi, type ChatMessage, type ChatRoom } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

type Props = { navigation: NativeStackNavigationProp<never> };

export function ChatScreen({ navigation }: Props) {
  const rooms = useApi(useCallback(() => chatApi.listRooms(), []));
  const [activeRoom, setActiveRoom] = useState<ChatRoom | null>(null);
  const [text, setText] = useState("");
  const { user } = useAuth();
  const listRef = useRef<FlatList>(null);

  const messages = useApi(
    useCallback(() => activeRoom ? chatApi.getMessages(activeRoom.room_id) : Promise.resolve({ messages:[], has_next:false }),
    [activeRoom?.room_id]));

  const sendAction = useAction(useCallback(
    (content:string) => chatApi.sendMessage(activeRoom!.room_id, content), [activeRoom?.room_id]
  ));

  useEffect(() => {
    if (activeRoom) chatApi.markRead(activeRoom.room_id).catch(()=>{});
  }, [activeRoom?.room_id]);

  useEffect(() => {
    if (messages.data?.messages.length)
      setTimeout(()=>listRef.current?.scrollToEnd({ animated:false }), 100);
  }, [messages.data]);

  async function handleSend() {
    const t = text.trim(); if (!t) return;
    setText("");
    const res = await sendAction.execute(t);
    if (res) messages.refetch();
  }

  const fmtTime = (d:string) => new Date(d).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"});

  if (!activeRoom) {
    // Room list
    return (
      <View style={gs.screen}>
        {rooms.loading ? (
          <View style={{padding:16,gap:14}}>{[...Array(4)].map((_,i)=><Skeleton key={i} height={70}/>)}</View>
        ) : (rooms.data?.rooms ?? []).length === 0 ? (
          <View style={{flex:1,alignItems:"center",justifyContent:"center",gap:12}}>
            <Text style={{fontSize:44}}>💬</Text>
            <Text style={{color:theme.colors.textTertiary,fontSize:theme.font.size.base}}>No conversations yet</Text>
            <Text style={{color:theme.colors.textTertiary,fontSize:theme.font.size.sm,textAlign:"center",paddingHorizontal:32}}>
              Messages from your technician will appear here
            </Text>
          </View>
        ) : (
          <FlatList data={rooms.data?.rooms??[]} keyExtractor={r=>r.room_id}
            renderItem={({item:r})=>(
              <TouchableOpacity style={s.roomRow} onPress={()=>setActiveRoom(r)} activeOpacity={0.85}>
                <View style={s.roomAvatar}><Text style={s.roomAvatarText}>{r.participant_name[0].toUpperCase()}</Text></View>
                <View style={{flex:1}}>
                  <View style={[gs.row,{justifyContent:"space-between"}]}>
                    <Text style={s.roomName}>{r.participant_name}</Text>
                    {r.last_message_at && <Text style={s.roomTime}>{fmtTime(r.last_message_at)}</Text>}
                  </View>
                  {r.job_number&&<Text style={s.roomJob}>Job: {r.job_number}</Text>}
                  {r.last_message&&<Text style={s.roomPreview} numberOfLines={1}>{r.last_message}</Text>}
                </View>
                {r.unread_count>0&&(
                  <View style={s.unreadBadge}><Text style={s.unreadText}>{r.unread_count}</Text></View>
                )}
              </TouchableOpacity>
            )}
            ItemSeparatorComponent={()=><View style={gs.sep}/>}
          />
        )}
      </View>
    );
  }

  // Message thread
  const renderMsg = ({item:m}:{item:ChatMessage}) => {
    const isMe = m.sender_id === user?.id;
    return (
      <View style={[s.msgRow, isMe?s.msgRight:s.msgLeft]}>
        <View style={[s.bubble, isMe?s.bubbleMe:s.bubbleOther]}>
          <Text style={[s.msgText, isMe&&{color:"#fff"}]}>{m.content}</Text>
        </View>
        <Text style={s.msgTime}>{fmtTime(m.sent_at)}</Text>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView style={{flex:1,backgroundColor:theme.colors.bg}}
      behavior={Platform.OS==="ios"?"padding":"height"} keyboardVerticalOffset={90}>
      {/* Header */}
      <TouchableOpacity style={s.threadHeader} onPress={()=>setActiveRoom(null)} activeOpacity={0.8}>
        <Text style={s.backBtn}>←</Text>
        <View style={s.roomAvatar}><Text style={s.roomAvatarText}>{activeRoom.participant_name[0].toUpperCase()}</Text></View>
        <View>
          <Text style={s.threadName}>{activeRoom.participant_name}</Text>
          {activeRoom.job_number&&<Text style={s.threadJob}>Job: {activeRoom.job_number}</Text>}
        </View>
      </TouchableOpacity>
      {/* Messages */}
      {messages.loading ? (
        <View style={{padding:16,gap:12}}>{[...Array(4)].map((_,i)=><Skeleton key={i} height={44}/>)}</View>
      ) : (
        <FlatList ref={listRef} data={messages.data?.messages??[]} keyExtractor={m=>m.message_id}
          renderItem={renderMsg} contentContainerStyle={{padding:14,gap:10}}/>
      )}
      {/* Input */}
      <View style={s.inputBar}>
        <TextInput style={s.input} value={text} onChangeText={setText}
          placeholder="Type a message…" placeholderTextColor={theme.colors.textTertiary}
          multiline maxLength={1000}/>
        <TouchableOpacity style={[s.sendBtn,!text.trim()&&{opacity:0.4}]}
          onPress={handleSend} disabled={!text.trim()||sendAction.loading}>
          <Text style={s.sendText}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  roomRow:       { flexDirection:"row", alignItems:"center", gap:12, padding:14, backgroundColor:theme.colors.surface },
  roomAvatar:    { width:44, height:44, borderRadius:22, backgroundColor:theme.colors.accentLight, alignItems:"center", justifyContent:"center" },
  roomAvatarText:{ fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.accent },
  roomName:      { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  roomTime:      { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  roomJob:       { fontSize:theme.font.size.xs, color:theme.colors.accent, fontWeight:"600", marginTop:1 },
  roomPreview:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  unreadBadge:   { width:20, height:20, borderRadius:10, backgroundColor:theme.colors.brand, alignItems:"center", justifyContent:"center" },
  unreadText:    { fontSize:9, fontWeight:"800", color:"#fff" },
  threadHeader:  { flexDirection:"row", alignItems:"center", gap:12, padding:14,
                   backgroundColor:theme.colors.surface, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  backBtn:       { fontSize:22, color:theme.colors.brand, fontWeight:"700" },
  threadName:    { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  threadJob:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  msgRow:        { maxWidth:"78%", gap:4 },
  msgLeft:       { alignSelf:"flex-start" },
  msgRight:      { alignSelf:"flex-end", alignItems:"flex-end" },
  bubble:        { borderRadius:16, paddingHorizontal:13, paddingVertical:9 },
  bubbleMe:      { backgroundColor:theme.colors.brand, borderBottomRightRadius:4 },
  bubbleOther:   { backgroundColor:theme.colors.surface, borderBottomLeftRadius:4, ...theme.shadow.sm },
  msgText:       { fontSize:theme.font.size.base, color:theme.colors.textPrimary, lineHeight:20 },
  msgTime:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  inputBar:      { flexDirection:"row", alignItems:"flex-end", gap:10, padding:12,
                   backgroundColor:theme.colors.surface, borderTopWidth:1, borderTopColor:theme.colors.border },
  input:         { flex:1, minHeight:40, maxHeight:100, borderWidth:1, borderColor:theme.colors.border,
                   borderRadius:20, paddingHorizontal:14, paddingVertical:9, fontSize:theme.font.size.base,
                   color:theme.colors.textPrimary, backgroundColor:theme.colors.surfaceSunken },
  sendBtn:       { width:40, height:40, borderRadius:20, backgroundColor:theme.colors.brand, alignItems:"center", justifyContent:"center" },
  sendText:      { color:"#fff", fontSize:20, fontWeight:"700" },
});
