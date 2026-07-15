import React, { useCallback } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { chatApi, type ChatThread } from "../lib/api";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

type Props = { navigation: NativeStackNavigationProp<never> };

// MODULE-L5-34: rewired to real ChatThread fields. There is no
// participant_name, last_message preview, or unread_count on the backend --
// threads are keyed by what they're about (record_type/record_id), not by
// who's in them.
const RECORD_LABELS: Record<string,string> = {
  service_booking: "Booking", service_job: "Job", complaint: "Complaint",
};

export function ChatListScreen({ navigation }: Props) {
  const threads = useApi(useCallback(() => chatApi.listThreads(), []));

  function renderThread({ item:t }: { item:ChatThread }) {
    const time = t.last_message_at
      ? new Date(t.last_message_at).toLocaleTimeString("en-IN",{ hour:"2-digit", minute:"2-digit" })
      : "";
    const label = RECORD_LABELS[t.record_type] ?? t.record_type;
    return (
      <TouchableOpacity style={s.row} activeOpacity={0.85}
        onPress={() => navigation.navigate("ChatRoom" as never,
          { threadId:t.id, title:`${label} · ${t.thread_number}` } as never)}>
        <View style={s.avatar}>
          <Text style={s.avatarText}>{label[0].toUpperCase()}</Text>
        </View>
        <View style={{ flex:1 }}>
          <View style={[gs.row, { justifyContent:"space-between" }]}>
            <Text style={s.name}>{label} · {t.thread_number}</Text>
            <Text style={s.time}>{time}</Text>
          </View>
          <Text style={s.jobRef}>{t.status}</Text>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <View style={gs.screen}>
      {threads.loading ? (
        <View style={{ padding:theme.spacing.base, gap:14 }}>
          {[...Array(5)].map((_,i) => <Skeleton key={i} height={70} />)}
        </View>
      ) : (
        <FlatList
          data={threads.data?.items ?? []}
          renderItem={renderThread}
          keyExtractor={t => t.id}
          onRefresh={threads.refetch}
          refreshing={threads.loading}
          ItemSeparatorComponent={() => <View style={gs.sep} />}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:80, gap:10 }}>
              <Text style={{ fontSize:48 }}>💬</Text>
              <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textTertiary }}>
                No conversations yet
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  row:        { flexDirection:"row", alignItems:"center", gap:12, padding:14, backgroundColor:theme.colors.surface },
  avatar:     { width:46, height:46, borderRadius:23, backgroundColor:theme.colors.accentLight,
                alignItems:"center", justifyContent:"center" },
  avatarText: { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.accent },
  name:       { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  time:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  jobRef:     { fontSize:theme.font.size.xs, color:theme.colors.accent, fontWeight:"600", marginTop:1 },
  preview:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  badge:      { width:22, height:22, borderRadius:11, backgroundColor:theme.colors.danger,
                alignItems:"center", justifyContent:"center" },
  badgeText:  { fontSize:9, fontWeight:"800", color:"#fff" },
});
